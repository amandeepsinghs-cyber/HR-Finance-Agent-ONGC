#!/usr/bin/env python3
"""medallion/bronze/load_bronze.py: Load structured landing files into BigQuery hrfin_bronze (Step 4.2).

Loads:
- CSV sources (sap, db_exports, governance) -> hrfin_bronze.<source>_<table>
  - All columns typed explicitly as STRING from headers (no autodetect)
  - Added metadata columns: _source_file (STRING), _ingest_ts (TIMESTAMP), _batch_id (STRING)
- Excel workbooks (excel) -> hrfin_bronze.excel_<table>
  - Converts every visible sheet to raw rows without cleaning
  - All cells as STRING (col_0, col_1, ... col_{max_cols-1})
  - Added metadata columns: _sheet_name (STRING), _row_number (INT64), _source_file (STRING), _ingest_ts (TIMESTAMP), _batch_id (STRING)

Idempotency:
- Uses WRITE_TRUNCATE / CREATE OR REPLACE TABLE per table.
- Generates medallion/bronze/bronze_tables.yaml with table metadata and row counts.
"""

from __future__ import annotations

import csv
import datetime
import io
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Tuple

import openpyxl
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from google.cloud import bigquery

PROJECT_ID = os.getenv("GCP_PROJECT", "ongc-hr-finance-agent")
ALLOWED_BRONZE_DATASETS = {"hrfin_bronze", "hrfin_bronze_v3"}
DATASET_ID = os.getenv("YUKTI_BRONZE_DATASET", "hrfin_bronze").strip()
if DATASET_ID not in ALLOWED_BRONZE_DATASETS:
    raise ValueError(f"Disallowed YUKTI_BRONZE_DATASET={DATASET_ID!r}; must be in {sorted(ALLOWED_BRONZE_DATASETS)}")
LANDING_BUCKET = "ongc-hr-finance-agent-landing"
BATCH_ID = os.getenv("YUKTI_BATCH_ID", "20261019")
LOAD_LOCAL = os.getenv("YUKTI_LOAD_LOCAL", "1") in ("1", "true", "yes")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LANDING_DIR = BASE_DIR / "landing"
BRONZE_YAML_PATH = Path(os.getenv("YUKTI_BRONZE_YAML_PATH", str(BASE_DIR / "medallion" / "bronze" / "bronze_tables.yaml")))

JOB_LABELS = {"datacloud": os.getenv("YUKTI_JOB_LABEL_VALUE", "jetski")}

# Non-canonical duplicate sources in landing/ (generator bug; dropped per Lead instructions)
NON_CANONICAL_DUPLICATES = {
    "landing/db_exports/corporate_financial_summary.csv",
    "landing/db_exports/subsidiary_group_financials.csv",
    "landing/governance/rti_applications_export.csv",
}


def get_csv_files() -> List[Dict[str, Any]]:
    """Collect all structured CSV files across sap, db_exports, and governance."""
    csv_items = []
    for src in ["sap", "db_exports", "governance"]:
        src_dir = LANDING_DIR / src
        if not src_dir.exists():
            continue
        for f in sorted(os.listdir(src_dir)):
            if not f.endswith(".csv"):
                continue
            fpath = src_dir / f
            local_rel = str(fpath.relative_to(BASE_DIR))
            if local_rel in NON_CANONICAL_DUPLICATES:
                continue
            base_name, _ = os.path.splitext(f)
            table_name = f"{src}_{base_name.lower()}"
            gcs_uri = f"gs://{LANDING_BUCKET}/{src}/{BATCH_ID}/{f}"
            with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                reader = csv.reader(fh)
                header = next(reader)
                row_count = sum(1 for _ in reader)
            csv_items.append({
                "source": src,
                "table_name": table_name,
                "file_name": f,
                "local_path": str(fpath.relative_to(BASE_DIR)),
                "full_path": str(fpath),
                "gcs_uri": gcs_uri,
                "header": header,
                "expected_rows": row_count,
            })
    return csv_items


def get_excel_files() -> List[Dict[str, Any]]:
    """Collect all structured Excel workbooks in landing/excel (excluding _clean)."""
    excel_items = []
    excel_dir = LANDING_DIR / "excel"
    for f in sorted(os.listdir(excel_dir)):
        if not f.endswith(".xlsx"):
            continue
        fpath = excel_dir / f
        base_name, _ = os.path.splitext(f)
        table_name = f"excel_{base_name.lower()}"
        gcs_uri = f"gs://{LANDING_BUCKET}/excel/{BATCH_ID}/{f}"

        # Quick scan of visible sheets and non-empty rows
        wb = openpyxl.load_workbook(str(fpath), data_only=True)
        visible_sheets = [s for s in wb.sheetnames if wb[s].sheet_state != "hidden"]
        expected_rows = 0
        max_cols = 0
        for s in visible_sheets:
            ws = wb[s]
            for r in ws.iter_rows(values_only=True):
                if any(c is not None and str(c).strip() != "" for c in r):
                    expected_rows += 1
                    max_cols = max(max_cols, len(r))
        wb.close()

        excel_items.append({
            "source": "excel",
            "table_name": table_name,
            "file_name": f,
            "local_path": str(fpath.relative_to(BASE_DIR)),
            "full_path": str(fpath),
            "gcs_uri": gcs_uri,
            "visible_sheets": visible_sheets,
            "expected_rows": expected_rows,
            "max_cols": max_cols,
        })
    return excel_items


def load_csv_table(client: bigquery.Client, item: Dict[str, Any], ingest_ts: datetime.datetime) -> Dict[str, Any]:
    """Load a CSV landing file from GCS to BigQuery hrfin_bronze using staging + CTAS."""
    table_name = item["table_name"]
    staging_table_id = f"{PROJECT_ID}.{DATASET_ID}._staging_{table_name}"
    final_table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
    gcs_uri = item["gcs_uri"]

    try:
        # 1. Load raw CSV from GCS to staging table with all STRING columns
        schema = [bigquery.SchemaField(col, "STRING") for col in item["header"]]
        load_config = bigquery.LoadJobConfig(
            schema=schema,
            skip_leading_rows=1,
            source_format=bigquery.SourceFormat.CSV,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            allow_quoted_newlines=True,
            encoding="UTF-8",
            labels=JOB_LABELS,
        )
        if LOAD_LOCAL and os.path.exists(item["full_path"]):
            with open(item["full_path"], "rb") as fh:
                load_job = client.load_table_from_file(fh, staging_table_id, job_config=load_config)
        else:
            load_job = client.load_table_from_uri(gcs_uri, staging_table_id, job_config=load_config)
        load_job.result()

        # 2. CTAS into final table adding metadata columns
        ts_iso = ingest_ts.isoformat()
        query = f"""
        CREATE OR REPLACE TABLE `{final_table_id}` AS
        SELECT
          *,
          "{gcs_uri}" AS _source_file,
          TIMESTAMP("{ts_iso}") AS _ingest_ts,
          "{BATCH_ID}" AS _batch_id
        FROM `{staging_table_id}`
        """
        query_job = client.query(query, job_config=bigquery.QueryJobConfig(labels=JOB_LABELS))
        query_job.result()

        # 3. Verify final table
        tbl = client.get_table(final_table_id)
        actual_rows = tbl.num_rows

        if actual_rows != item["expected_rows"]:
            raise ValueError(f"Row count mismatch for {table_name}: expected {item['expected_rows']}, got {actual_rows}")

        return {
            "status": "success",
            "table_name": table_name,
            "rows": actual_rows,
            "cols": len(tbl.schema),
            "columns": [f.name for f in tbl.schema],
            "error": None,
        }
    except Exception as e:
        return {
            "status": "failed",
            "table_name": table_name,
            "rows": 0,
            "cols": 0,
            "columns": [],
            "error": str(e),
        }
    finally:
        client.delete_table(staging_table_id, not_found_ok=True)


def load_excel_table(client: bigquery.Client, item: Dict[str, Any], ingest_ts: datetime.datetime) -> Dict[str, Any]:
    """Convert Excel visible sheets to raw rows and load to BigQuery hrfin_bronze."""
    table_name = item["table_name"]
    final_table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
    gcs_uri = item["gcs_uri"]

    try:
        wb = openpyxl.load_workbook(item["full_path"], data_only=True)
        visible_sheets = [s for s in wb.sheetnames if wb[s].sheet_state != "hidden"]

        rows_data: List[Dict[str, Any]] = []
        max_cols = item["max_cols"]

        for sname in visible_sheets:
            ws = wb[sname]
            for row_idx, r in enumerate(ws.iter_rows(values_only=True), start=1):
                if not any(c is not None and str(c).strip() != "" for c in r):
                    continue
                row_dict: Dict[str, Any] = {
                    "_sheet_name": sname,
                    "_row_number": row_idx,
                }
                for col_idx, c in enumerate(r):
                    val_str = None if c is None else str(c)
                    row_dict[f"col_{col_idx}"] = val_str
                rows_data.append(row_dict)
        wb.close()

        # Build PyArrow schema and table
        arrow_fields = [
            pa.field("_sheet_name", pa.string()),
            pa.field("_row_number", pa.int64()),
        ]
        for c_idx in range(max_cols):
            arrow_fields.append(pa.field(f"col_{c_idx}", pa.string()))
        arrow_fields.extend([
            pa.field("_source_file", pa.string()),
            pa.field("_ingest_ts", pa.timestamp("us", tz="UTC")),
            pa.field("_batch_id", pa.string()),
        ])
        arrow_schema = pa.schema(arrow_fields)

        # Build column-oriented arrays
        col_arrays = {f.name: [] for f in arrow_schema}
        for rd in rows_data:
            col_arrays["_sheet_name"].append(rd["_sheet_name"])
            col_arrays["_row_number"].append(rd["_row_number"])
            for c_idx in range(max_cols):
                col_arrays[f"col_{c_idx}"].append(rd.get(f"col_{c_idx}"))
            col_arrays["_source_file"].append(gcs_uri)
            col_arrays["_ingest_ts"].append(ingest_ts)
            col_arrays["_batch_id"].append(BATCH_ID)

        arrow_table = pa.Table.from_pydict(col_arrays, schema=arrow_schema)

        # Write to in-memory parquet buffer
        buf = io.BytesIO()
        pq.write_table(arrow_table, buf)
        buf.seek(0)

        # Load into BigQuery
        load_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            labels=JOB_LABELS,
        )
        job = client.load_table_from_file(buf, final_table_id, job_config=load_config)
        job.result()

        tbl = client.get_table(final_table_id)
        actual_rows = tbl.num_rows

        if actual_rows != item["expected_rows"]:
            raise ValueError(f"Row count mismatch for {table_name}: expected {item['expected_rows']}, got {actual_rows}")

        return {
            "status": "success",
            "table_name": table_name,
            "rows": actual_rows,
            "cols": len(tbl.schema),
            "columns": [f.name for f in tbl.schema],
            "error": None,
        }
    except Exception as e:
        return {
            "status": "failed",
            "table_name": table_name,
            "rows": 0,
            "cols": 0,
            "columns": [],
            "error": str(e),
        }


def main():
    print(f"[{time.strftime('%X')}] Scanning structured landing files for Bronze ingestion...")
    csv_items = get_csv_files()
    excel_items = get_excel_files()
    all_items = csv_items + excel_items
    print(f"Discovered {len(csv_items)} CSV files and {len(excel_items)} Excel files (Total: {len(all_items)} tables)")

    total_expected_rows = sum(it["expected_rows"] for it in all_items)
    print(f"Total expected rows across all 45 tables: {total_expected_rows}")

    client = bigquery.Client(project=PROJECT_ID)
    ingest_ts = datetime.datetime.now(datetime.timezone.utc)
    start_time = time.time()

    table_results: Dict[str, Dict[str, Any]] = {}
    failed: List[str] = []

    # 1. Load CSV tables concurrently
    print(f"[{time.strftime('%X')}] Loading {len(csv_items)} CSV tables in parallel (6 workers)...")
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(load_csv_table, client, item, ingest_ts): item for item in csv_items}
        for future in as_completed(futures):
            res = future.result()
            tname = res["table_name"]
            table_results[tname] = res
            if res["status"] == "failed":
                failed.append(tname)
                print(f"  [FAIL] {tname}: {res['error']}")
            else:
                print(f"  [OK] {tname:35}: {res['rows']:10d} rows, {res['cols']} cols")

    # 2. Load Excel tables sequentially (memory-safe and fast)
    print(f"[{time.strftime('%X')}] Loading {len(excel_items)} Excel workbooks...")
    for item in excel_items:
        res = load_excel_table(client, item, ingest_ts)
        tname = res["table_name"]
        table_results[tname] = res
        if res["status"] == "failed":
            failed.append(tname)
            print(f"  [FAIL] {tname}: {res['error']}")
        else:
            print(f"  [OK] {tname:35}: {res['rows']:10d} rows, {res['cols']} cols")

    elapsed = time.time() - start_time
    print(f"[{time.strftime('%X')}] Ingestion finished in {elapsed:.1f}s. Success: {len(table_results) - len(failed)}/45, Failed: {len(failed)}")

    if failed:
        print(f"Ingestion failed on tables: {failed}")
        sys.exit(1)

    # 3. Write bronze_tables.yaml
    yaml_data: Dict[str, Any] = {
        "version": "1.0",
        "generated_at": ingest_ts.isoformat(),
        "batch_id": BATCH_ID,
        "project_id": PROJECT_ID,
        "dataset_id": DATASET_ID,
        "total_tables": len(all_items),
        "total_rows": sum(res["rows"] for res in table_results.values()),
        "tables": {},
    }

    for item in all_items:
        tname = item["table_name"]
        res = table_results[tname]
        yaml_data["tables"][tname] = {
            "source_type": item["source"],
            "source_file": item["gcs_uri"],
            "local_path": item["local_path"],
            "row_count": res["rows"],
            "column_count": res["cols"],
            "columns": res["columns"],
        }

    BRONZE_YAML_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BRONZE_YAML_PATH, "w", encoding="utf-8") as f:
        yaml.dump(yaml_data, f, sort_keys=False, default_flow_style=False)

    print(f"[{time.strftime('%X')}] Wrote Bronze metadata to {BRONZE_YAML_PATH}")
    print("Bronze loading fully completed successfully.")


if __name__ == "__main__":
    main()
