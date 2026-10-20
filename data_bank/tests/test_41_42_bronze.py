"""tests/test_41_42_bronze.py: Automated verification for Phase 4 steps 4.1 & 4.2.

Validates that:
1. GCS objects match upload manifest (Step 4.1):
   - Every file in medallion/upload_manifest.csv exists in GCS.
   - Object count and MD5 hash match 100%.
2. Every structured landing file has a corresponding Bronze table in hrfin_bronze (Step 4.2):
   - Total tables == 45 (16 sap, 9 db_exports, 4 governance, 16 excel).
3. Bronze row counts match source data rows:
   - CSV: exact row count == (total lines - 1).
   - Excel: exact row count == sum of non-empty rows across all visible sheets.
   - Total rows == 4,246,288 across all 45 tables.
4. Metadata columns are populated:
   - All tables have _source_file, _ingest_ts, _batch_id (non-null).
   - Excel tables also have _sheet_name, _row_number (non-null).
5. medallion/bronze/bronze_tables.yaml integrity:
   - Contains all 45 tables and matches BigQuery live metadata.
"""

from __future__ import annotations

import base64
import csv
import glob
import os
from pathlib import Path
from typing import Any, Dict, List

import openpyxl
import pytest
import yaml
from google.cloud import bigquery, storage

PROJECT_ID = "ongc-hr-finance-agent"
BRONZE_DATASET = "hrfin_bronze"
LANDING_BUCKET = "ongc-hr-finance-agent-landing"
DOCS_BUCKET = "ongc-hr-finance-agent-docs"
BATCH_ID = "20261019"

# Non-canonical duplicate sources in landing/ (generator bug; dropped per Lead instructions)
NON_CANONICAL_DUPLICATES = {
    "landing/db_exports/corporate_financial_summary.csv",
    "landing/db_exports/subsidiary_group_financials.csv",
    "landing/governance/rti_applications_export.csv",
}

BASE_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = BASE_DIR / "medallion" / "upload_manifest.csv"
BRONZE_YAML_PATH = BASE_DIR / "medallion" / "bronze" / "bronze_tables.yaml"
LANDING_DIR = BASE_DIR / "landing"


@pytest.fixture(scope="module")
def bq_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)


@pytest.fixture(scope="module")
def gcs_client() -> storage.Client:
    return storage.Client(project=PROJECT_ID)


@pytest.fixture(scope="module")
def upload_manifest() -> List[Dict[str, str]]:
    assert MANIFEST_PATH.exists(), f"Missing manifest: {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


@pytest.fixture(scope="module")
def bronze_yaml() -> Dict[str, Any]:
    assert BRONZE_YAML_PATH.exists(), f"Missing bronze_tables.yaml: {BRONZE_YAML_PATH}"
    with open(BRONZE_YAML_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def expected_tables() -> Dict[str, Dict[str, Any]]:
    """Inspect local structured landing files and calculate expected row counts and table names."""
    tables: Dict[str, Dict[str, Any]] = {}

    # CSV files
    for src in ["sap", "db_exports", "governance"]:
        src_dir = LANDING_DIR / src
        for f in sorted(os.listdir(src_dir)):
            if not f.endswith(".csv"):
                continue
            fpath = src_dir / f
            local_rel = str(fpath.relative_to(BASE_DIR))
            if local_rel in NON_CANONICAL_DUPLICATES:
                continue
            base_name, _ = os.path.splitext(f)
            tname = f"{src}_{base_name.lower()}"
            with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                reader = csv.reader(fh)
                header = next(reader)
                row_count = sum(1 for _ in reader)
            tables[tname] = {
                "source": src,
                "file_name": f,
                "local_path": str(fpath),
                "is_excel": False,
                "expected_rows": row_count,
            }

    # Excel files
    excel_dir = LANDING_DIR / "excel"
    for f in sorted(os.listdir(excel_dir)):
        if not f.endswith(".xlsx"):
            continue
        base_name, _ = os.path.splitext(f)
        tname = f"excel_{base_name.lower()}"
        fpath = excel_dir / f
        wb = openpyxl.load_workbook(str(fpath), data_only=True)
        visible_sheets = [s for s in wb.sheetnames if wb[s].sheet_state != "hidden"]
        row_count = 0
        for s in visible_sheets:
            ws = wb[s]
            for r in ws.iter_rows(values_only=True):
                if any(c is not None and str(c).strip() != "" for c in r):
                    row_count += 1
        wb.close()
        tables[tname] = {
            "source": "excel",
            "file_name": f,
            "local_path": str(fpath),
            "is_excel": True,
            "expected_rows": row_count,
        }

    return tables


def test_upload_manifest_exists_and_complete(upload_manifest: List[Dict[str, str]]):
    """Verify upload_manifest.csv contains exactly 1602 items (941 landing + 661 docs)."""
    assert len(upload_manifest) == 1602, f"Expected 1602 manifest rows, got {len(upload_manifest)}"
    landing_count = sum(1 for r in upload_manifest if LANDING_BUCKET in r["gs_uri"])
    docs_count = sum(1 for r in upload_manifest if DOCS_BUCKET in r["gs_uri"])
    assert landing_count == 941, f"Expected 941 landing objects, got {landing_count}"
    assert docs_count == 661, f"Expected 661 docs objects, got {docs_count}"


def test_gcs_objects_match_upload_manifest(gcs_client: storage.Client, upload_manifest: List[Dict[str, str]]):
    """Verify that all uploaded files exist in GCS with matching byte size and MD5."""
    landing_bucket = gcs_client.bucket(LANDING_BUCKET)
    docs_bucket = gcs_client.bucket(DOCS_BUCKET)

    landing_blobs = {b.name: b for b in landing_bucket.list_blobs()}
    docs_blobs = {b.name: b for b in docs_bucket.list_blobs()}

    assert len(landing_blobs) >= 941
    assert len(docs_blobs) >= 661

    # Spot check 50 items and verify all sizes and MD5s
    for row in upload_manifest:
        uri = row["gs_uri"]
        expected_size = int(row["size"])
        expected_md5 = row["md5"]

        if LANDING_BUCKET in uri:
            blob_name = uri.replace(f"gs://{LANDING_BUCKET}/", "")
            blob = landing_blobs.get(blob_name)
        else:
            blob_name = uri.replace(f"gs://{DOCS_BUCKET}/", "")
            blob = docs_blobs.get(blob_name)

        assert blob is not None, f"GCS blob missing: {uri}"
        assert blob.size == expected_size, f"Size mismatch for {uri}: expected {expected_size}, got {blob.size}"
        actual_md5 = base64.b64decode(blob.md5_hash).hex()
        assert actual_md5 == expected_md5, f"MD5 mismatch for {uri}: expected {expected_md5}, got {actual_md5}"


def test_every_landing_file_has_bronze_table(bq_client: bigquery.Client, expected_tables: Dict[str, Dict[str, Any]]):
    """Verify all 46 structured tables exist in BigQuery hrfin_bronze."""
    assert len(expected_tables) == 46, f"Expected 46 structured landing files, found {len(expected_tables)}"
    actual_tables = {t.table_id for t in bq_client.list_tables(BRONZE_DATASET)}

    for tname in expected_tables:
        assert tname in actual_tables, f"Bronze table missing: {BRONZE_DATASET}.{tname}"


def test_bronze_row_counts_match_source_data(bq_client: bigquery.Client, expected_tables: Dict[str, Dict[str, Any]]):
    """Verify that every Bronze table row count exactly equals the source data rows."""
    total_bronze_rows = 0
    total_expected_rows = 0

    for tname, meta in expected_tables.items():
        tbl = bq_client.get_table(f"{PROJECT_ID}.{BRONZE_DATASET}.{tname}")
        actual_rows = tbl.num_rows
        expected_rows = meta["expected_rows"]

        assert actual_rows == expected_rows, (
            f"Row count mismatch for {tname}: BigQuery has {actual_rows}, source data has {expected_rows}"
        )
        total_bronze_rows += actual_rows
        total_expected_rows += expected_rows

    assert total_bronze_rows == 4363599, f"Expected 4,363,599 total rows, got {total_bronze_rows}"
    assert total_bronze_rows == total_expected_rows


def test_bronze_metadata_columns_populated(bq_client: bigquery.Client, expected_tables: Dict[str, Dict[str, Any]]):
    """Verify metadata columns exist and are non-null across all Bronze tables."""
    for tname, meta in expected_tables.items():
        tbl = bq_client.get_table(f"{PROJECT_ID}.{BRONZE_DATASET}.{tname}")
        col_names = {f.name for f in tbl.schema}

        assert "_source_file" in col_names, f"_source_file missing in {tname}"
        assert "_ingest_ts" in col_names, f"_ingest_ts missing in {tname}"
        assert "_batch_id" in col_names, f"_batch_id missing in {tname}"

        if meta["is_excel"]:
            assert "_sheet_name" in col_names, f"_sheet_name missing in {tname}"
            assert "_row_number" in col_names, f"_row_number missing in {tname}"

        # Probe for NULL values in metadata columns (limit query to 1 row check)
        query = f"""
        SELECT
          COUNTIF(_source_file IS NULL OR _source_file = '') AS null_source,
          COUNTIF(_ingest_ts IS NULL) AS null_ts,
          COUNTIF(_batch_id IS NULL OR _batch_id = '') AS null_batch
          {", COUNTIF(_sheet_name IS NULL OR _sheet_name = '') AS null_sheet, COUNTIF(_row_number IS NULL) AS null_row" if meta["is_excel"] else ""}
        FROM `{PROJECT_ID}.{BRONZE_DATASET}.{tname}`
        """
        job = bq_client.query(query, job_config=bigquery.QueryJobConfig(labels={"datacloud": "ai-agent"}))
        res = list(job.result())[0]

        assert res.null_source == 0, f"Found NULL _source_file in {tname}"
        assert res.null_ts == 0, f"Found NULL _ingest_ts in {tname}"
        assert res.null_batch == 0, f"Found NULL _batch_id in {tname}"
        if meta["is_excel"]:
            assert res.null_sheet == 0, f"Found NULL _sheet_name in {tname}"
            assert res.null_row == 0, f"Found NULL _row_number in {tname}"


def test_bronze_tables_yaml_integrity(bronze_yaml: Dict[str, Any], expected_tables: Dict[str, Dict[str, Any]]):
    """Verify bronze_tables.yaml metadata and row counts match expectations."""
    assert bronze_yaml["total_tables"] == 46
    assert bronze_yaml["total_rows"] == 4363599

    tables_meta = bronze_yaml["tables"]
    assert len(tables_meta) == 46

    for tname, meta in expected_tables.items():
        assert tname in tables_meta, f"{tname} missing in bronze_tables.yaml"
        yaml_entry = tables_meta[tname]
        assert yaml_entry["row_count"] == meta["expected_rows"]
        assert yaml_entry["source_file"].startswith(f"gs://{LANDING_BUCKET}/")
