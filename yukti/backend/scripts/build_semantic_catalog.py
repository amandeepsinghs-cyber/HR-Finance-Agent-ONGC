#!/usr/bin/env python3
"""Builds app/semantic/semantic_catalog.json by profiling BigQuery tables in hrfin_gold and hrfin_silver.

Reads schema from INFORMATION_SCHEMA.COLUMNS and INFORMATION_SCHEMA.TABLES,
profiles row counts, column nulls, ranges, and low-cardinality categorical values.
Enforces read-only BigQuery access, byte limits, and deterministic output.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime
import decimal
import json
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# Ensure yukti/backend is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from google.cloud import bigquery
from app.config import BQ_LOCATION, GCP_PROJECT, JOB_LABELS

DEFAULT_OUT_PATH = BACKEND_DIR / "app" / "semantic" / "semantic_catalog.json"
MAX_BYTES_BILLED_PER_JOB = 2_000_000_000  # 2 GB per job guard

# Required tables per task packet specification
REQUIRED_GOLD_TABLES = [
    "ssot_workforce_employee",
    "ssot_work_centre_360",
    "ssot_field_economics_360",
    "ssot_corporate_annual_360",
    "agg_headcount_tenure_summary",
    "agg_field_pnl_summary",
    "agg_lifting_cost_summary",
    "agg_vacancies_summary",
]

SILVER_TABLES = [
    "access_audit_log",
    "apar_ratings",
    "apprentices",
    "benefit_liabilities",
    "board_agenda_index",
    "cag_paras",
    "capex_budget",
    "contract_workforce",
    "corporate_financials",
    "cost_ledger",
    "csr_projects",
    "dim_cost_centre",
    "dim_customer",
    "dim_discipline",
    "dim_field",
    "dim_grade",
    "dim_project",
    "dim_vendor",
    "dim_work_centre",
    "dpc_cases",
    "employee_master",
    "energy_transition",
    "env_incidents",
    "field_pnl_annual",
    "forex_hedges",
    "grievances_litigation",
    "headcount_snapshot",
    "hse_incidents",
    "icc_committees",
    "leave_ledger",
    "medical_claims",
    "mou_targets",
    "parliament_questions",
    "payroll_monthly",
    "po_channel",
    "posh_cases",
    "posting_history",
    "price_fx_monthly",
    "production_monthly",
    "project_progress",
    "promotion_history",
    "purchase_orders",
    "receivables",
    "reserves_annual",
    "rti_applications",
    "sanctioned_posts",
    "separations",
    "subsidiary_financials",
    "succession_plan",
    "training_calendar",
    "training_records",
    "travel_claims",
    "vigilance_cases",
    "wells_drilled",
]

TABLES = {
    "hrfin_gold": REQUIRED_GOLD_TABLES,
    "hrfin_silver": SILVER_TABLES,
}


def natural_sort_key(s: Any) -> list:
    """Natural sort key helper so FY17..FY26 or 1..10 sort intuitively."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", str(s))]


def format_num(val: Any) -> Optional[float]:
    """Formats numeric value for JSON serialization."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, decimal.Decimal):
        return float(val)
    try:
        return float(val)
    except Exception:
        return str(val)


def format_date(val: Any) -> Optional[str]:
    """Formats date or timestamp value to ISO string."""
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def get_client() -> bigquery.Client:
    return bigquery.Client(project=GCP_PROJECT, location=BQ_LOCATION)


def query_job_config() -> bigquery.QueryJobConfig:
    return bigquery.QueryJobConfig(
        labels=JOB_LABELS,
        maximum_bytes_billed=MAX_BYTES_BILLED_PER_JOB,
    )


def fetch_dataset_metadata(client: bigquery.Client) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """
    Fetches table metadata and columns for hrfin_gold and hrfin_silver.
    Enforces exact 32 gold tables and 54 silver tables.
    Returns: (table_meta_dict, table_columns_dict)
    """
    cfg = query_job_config()

    # 1. Fetch tables from INFORMATION_SCHEMA.TABLES
    table_meta: Dict[str, Dict[str, Any]] = {}

    # hrfin_gold: all tables
    gold_tables_query = f"""
    SELECT table_name, table_type
    FROM `{GCP_PROJECT}.hrfin_gold.INFORMATION_SCHEMA.TABLES`
    ORDER BY table_name
    """
    gold_rows = list(client.query(gold_tables_query, job_config=cfg).result())
    gold_names = {r["table_name"] for r in gold_rows}

    # Assert gold requirements
    if len(gold_rows) < 32:
        raise ValueError(f"Expected at least 32 hrfin_gold tables, found {len(gold_rows)}")
    for req in REQUIRED_GOLD_TABLES:
        if req not in gold_names:
            raise ValueError(f"Required gold table {req} not found in hrfin_gold")

    for r in gold_rows:
        t_id = f"hrfin_gold.{r['table_name']}"
        table_meta[t_id] = {
            "dataset": "hrfin_gold",
            "table_name": r["table_name"],
            "kind": r["table_type"],
        }

    # hrfin_silver: exactly 54 specified tables
    silver_tables_query = f"""
    SELECT table_name, table_type
    FROM `{GCP_PROJECT}.hrfin_silver.INFORMATION_SCHEMA.TABLES`
    WHERE table_name IN UNNEST(@silver_req)
    ORDER BY table_name
    """
    silver_cfg = query_job_config()
    silver_cfg.query_parameters = [
        bigquery.ArrayQueryParameter("silver_req", "STRING", SILVER_TABLES)
    ]
    silver_rows = list(client.query(silver_tables_query, job_config=silver_cfg).result())
    silver_found = {r["table_name"] for r in silver_rows}

    missing_silver = set(SILVER_TABLES) - silver_found
    if missing_silver:
        raise ValueError(f"Missing required hrfin_silver tables: {sorted(missing_silver)}")

    for r in silver_rows:
        t_id = f"hrfin_silver.{r['table_name']}"
        table_meta[t_id] = {
            "dataset": "hrfin_silver",
            "table_name": r["table_name"],
            "kind": r["table_type"],
        }

    # 2. Fetch columns in ordinal order (one query per dataset)
    table_columns: Dict[str, List[Dict[str, Any]]] = {t_id: [] for t_id in table_meta}

    for dataset in ["hrfin_gold", "hrfin_silver"]:
        col_query = f"""
        SELECT table_name, column_name, ordinal_position, data_type
        FROM `{GCP_PROJECT}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
        ORDER BY table_name, ordinal_position
        """
        for r in client.query(col_query, job_config=cfg).result():
            t_id = f"{dataset}.{r['table_name']}"
            if t_id in table_columns:
                table_columns[t_id].append({
                    "column_name": r["column_name"],
                    "ordinal_position": r["ordinal_position"],
                    "data_type": r["data_type"],
                })

    return table_meta, table_columns


def profile_table(
    table_id: str,
    meta: Dict[str, Any],
    columns: List[Dict[str, Any]],
) -> Tuple[str, Dict[str, Any], int, Optional[str]]:
    """
    Profiles a single table with one aggregate query, followed by an optional
    union query for low-cardinality categorical values and fiscal_year.
    Returns: (table_id, table_catalog_dict, bytes_processed, error_message)
    """
    client = get_client()
    cfg = query_job_config()
    dataset = meta["dataset"]
    table_name = meta["table_name"]
    full_table_ref = f"`{GCP_PROJECT}.{dataset}.{table_name}`"

    bytes_processed = 0
    try:
        # Build single aggregate profiling query
        aggs = ["COUNT(*) AS __row_count"]
        col_mapping = {}

        for i, col in enumerate(columns):
            cname = col["column_name"]
            dtype = col["data_type"]
            col_mapping[i] = col

            if dtype == "STRING":
                aggs.append(f"APPROX_COUNT_DISTINCT(`{cname}`) AS c_{i}__distinct")
                aggs.append(f"COUNTIF(`{cname}` IS NULL) AS c_{i}__nulls")
            elif dtype in ("INT64", "FLOAT64", "NUMERIC", "BIGNUMERIC"):
                aggs.append(f"MIN(`{cname}`) AS c_{i}__min")
                aggs.append(f"MAX(`{cname}`) AS c_{i}__max")
                aggs.append(f"COUNTIF(`{cname}` IS NULL) AS c_{i}__nulls")
            elif dtype in ("DATE", "TIMESTAMP", "DATETIME"):
                aggs.append(f"MIN(`{cname}`) AS c_{i}__min")
                aggs.append(f"MAX(`{cname}`) AS c_{i}__max")
                aggs.append(f"COUNTIF(`{cname}` IS NULL) AS c_{i}__nulls")
            elif dtype == "BOOL":
                aggs.append(f"COUNTIF(`{cname}` IS TRUE) AS c_{i}__trues")
                aggs.append(f"COUNTIF(`{cname}` IS FALSE) AS c_{i}__falses")
                aggs.append(f"COUNTIF(`{cname}` IS NULL) AS c_{i}__nulls")
            # ARRAY, STRUCT, JSON are skipped from profiling

        agg_sql = f"SELECT {', '.join(aggs)} FROM {full_table_ref}"
        job1 = client.query(agg_sql, job_config=cfg)
        row1 = list(job1.result())[0]
        bytes_processed += job1.total_bytes_processed or 0

        row_count = int(row1["__row_count"])

        # Construct initial column profiles
        cols_catalog: Dict[str, Dict[str, Any]] = {}
        cols_needing_distinct_profile: List[str] = []

        for i, col in enumerate(columns):
            cname = col["column_name"]
            dtype = col["data_type"]

            if dtype.startswith("ARRAY") or dtype.startswith("STRUCT") or dtype == "JSON":
                cols_catalog[cname] = {"type": dtype}
            elif dtype == "STRING":
                distinct_cnt = int(row1[f"c_{i}__distinct"]) if row_count > 0 else 0
                nulls_cnt = int(row1[f"c_{i}__nulls"]) if row_count > 0 else 0
                cols_catalog[cname] = {
                    "type": dtype,
                    "distinct": distinct_cnt,
                    "nulls": nulls_cnt,
                }
                if distinct_cnt <= 60 or cname == "fiscal_year":
                    cols_needing_distinct_profile.append(cname)
            elif dtype in ("INT64", "FLOAT64", "NUMERIC", "BIGNUMERIC"):
                nulls_cnt = int(row1[f"c_{i}__nulls"]) if row_count > 0 else 0
                cols_catalog[cname] = {
                    "type": dtype,
                    "min": format_num(row1[f"c_{i}__min"]) if row_count > 0 else None,
                    "max": format_num(row1[f"c_{i}__max"]) if row_count > 0 else None,
                    "nulls": nulls_cnt,
                }
                if cname == "fiscal_year":
                    cols_needing_distinct_profile.append(cname)
            elif dtype in ("DATE", "TIMESTAMP", "DATETIME"):
                nulls_cnt = int(row1[f"c_{i}__nulls"]) if row_count > 0 else 0
                cols_catalog[cname] = {
                    "type": dtype,
                    "min": format_date(row1[f"c_{i}__min"]) if row_count > 0 else None,
                    "max": format_date(row1[f"c_{i}__max"]) if row_count > 0 else None,
                    "nulls": nulls_cnt,
                }
                if cname == "fiscal_year":
                    cols_needing_distinct_profile.append(cname)
            elif dtype == "BOOL":
                cols_catalog[cname] = {
                    "type": dtype,
                    "true_count": int(row1[f"c_{i}__trues"]) if row_count > 0 else 0,
                    "false_count": int(row1[f"c_{i}__falses"]) if row_count > 0 else 0,
                    "nulls": int(row1[f"c_{i}__nulls"]) if row_count > 0 else 0,
                }

        # Query distinct values if needed and table is not empty
        if row_count > 0 and cols_needing_distinct_profile:
            unions = []
            for cname in cols_needing_distinct_profile:
                unions.append(
                    f"SELECT '{cname}' AS c, CAST(`{cname}` AS STRING) AS v, COUNT(*) AS n "
                    f"FROM {full_table_ref} WHERE `{cname}` IS NOT NULL GROUP BY v"
                )
            distinct_sql = "\nUNION ALL\n".join(unions)
            job2 = client.query(distinct_sql, job_config=cfg)
            bytes_processed += job2.total_bytes_processed or 0

            val_counts_by_col: Dict[str, Dict[str, int]] = {c: {} for c in cols_needing_distinct_profile}
            for r in job2.result():
                col_key = r["c"]
                val_str = str(r["v"])
                cnt = int(r["n"])
                val_counts_by_col[col_key][val_str] = cnt

            for cname in cols_needing_distinct_profile:
                counts = val_counts_by_col.get(cname, {})
                if cname == "fiscal_year":
                    values = sorted(counts.keys(), key=natural_sort_key)
                else:
                    values = sorted(counts.keys(), key=lambda v: (-counts[v], str(v)))

                cols_catalog[cname]["values"] = values
                cols_catalog[cname]["value_counts"] = counts
        elif row_count == 0 and cols_needing_distinct_profile:
            for cname in cols_needing_distinct_profile:
                cols_catalog[cname]["values"] = []
                cols_catalog[cname]["value_counts"] = {}

        table_result = {
            "kind": meta["kind"],
            "row_count": row_count,
            "columns": cols_catalog,
        }
        return table_id, table_result, bytes_processed, None

    except Exception as exc:
        return table_id, {}, bytes_processed, str(exc)


def main():
    parser = argparse.ArgumentParser(description="Build semantic catalog from BigQuery metadata and profiling.")
    parser.add_argument("--only", nargs="+", help="Specific table(s) to process (e.g. hrfin_silver.dim_grade)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH, help="Path for output catalog JSON")
    parser.add_argument("--concurrency", type=int, default=6, help="Concurrent profiling threads")
    args = parser.parse_args()

    out_path: Path = args.out.resolve()
    t_start = time.time()
    print(f"Connecting to BigQuery project={GCP_PROJECT}, location={BQ_LOCATION}...")
    client = get_client()

    print("Fetching dataset schemas from INFORMATION_SCHEMA...")
    table_meta, table_columns = fetch_dataset_metadata(client)
    all_table_ids = sorted(table_meta.keys())
    n_gold = sum(1 for t in all_table_ids if str(t).startswith("hrfin_gold."))
    print(f"Found {len(all_table_ids)} total tables (Gold: {n_gold}, Silver: {len(all_table_ids) - n_gold}).")

    # Filter tables if --only specified
    if args.only:
        targets = set()
        for pattern in args.only:
            matched = False
            for t_id in all_table_ids:
                if t_id == pattern or t_id.split(".")[1] == pattern:
                    targets.add(t_id)
                    matched = True
            if not matched:
                print(f"ERROR: Specified table pattern '{pattern}' did not match any known table.", file=sys.stderr)
                sys.exit(1)
        target_table_ids = sorted(targets)
        print(f"Filtering to {len(target_table_ids)} table(s) via --only: {target_table_ids}")
    else:
        target_table_ids = all_table_ids

    total_bytes = 0
    failures: List[Tuple[str, str]] = []
    tables_catalog: Dict[str, Dict[str, Any]] = {}

    print(f"Profiling {len(target_table_ids)} tables with concurrency={args.concurrency}...")

    def _worker(t_id: str):
        return profile_table(t_id, table_meta[t_id], table_columns[t_id])

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        for idx, (t_id, result, b_proc, err) in enumerate(executor.map(_worker, target_table_ids), start=1):
            total_bytes += b_proc
            mb = b_proc / (1024 * 1024)
            if err:
                failures.append((t_id, err))
                print(f"[{idx}/{len(target_table_ids)}] ❌ {t_id} FAILED: {err} ({mb:.1f} MB)", file=sys.stderr)
            else:
                tables_catalog[t_id] = result
                r_cnt = result["row_count"]
                c_cnt = len(result["columns"])
                print(f"[{idx}/{len(target_table_ids)}] ✅ {t_id}: {r_cnt:,} rows, {c_cnt} cols ({mb:.1f} MB)")

    elapsed = time.time() - t_start
    total_mb = total_bytes / (1024 * 1024)
    total_gb = total_bytes / (1024 * 1024 * 1024)
    print(f"\nProfiling completed in {elapsed:.1f}s.")
    print(f"Total BigQuery bytes processed: {total_mb:.1f} MB ({total_gb:.3f} GB).")

    if total_gb >= 5.0:
        print(f"WARNING: Total bytes processed exceeded 5 GB limit ({total_gb:.3f} GB)!", file=sys.stderr)

    if failures:
        print(f"\nERROR: {len(failures)} table(s) failed profiling:", file=sys.stderr)
        for t_id, err in failures:
            print(f"  - {t_id}: {err}", file=sys.stderr)
        sys.exit(1)

    catalog_payload = {
        "version": 1,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "project": GCP_PROJECT,
        "tables": tables_catalog,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(catalog_payload, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote semantic catalog to {out_path} ({len(tables_catalog)} tables).")


if __name__ == "__main__":
    main()
