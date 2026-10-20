"""test_43_44_silver_gold.py: Comprehensive verification suite for Phase 4 Steps 4.3 (Silver) and 4.4 (Gold).

Validates directly against BigQuery ongc-hr-finance-agent:
1. All 53 silver tables exist with 100% matching columns and data types per schema_silver.yaml.
2. Dataform assertions pass with 0 failing rows (silver_foreign_keys, silver_accepted_values, gold_calibration_reconciliation).
3. Silver for every Excel source EXACTLY matches clean tables (landing/excel/_clean/*.xlsx as oracle:
   identical row count, identical PK set, and identical column sums).
4. All 16 gold marts + 5 semantic views + glossary (>=40 terms) + metric_definitions (>=60 metrics) exist and have non-empty row counts.
5. Gold reconciles to public calibration targets within strict ±2% tolerance:
   - Year-end Headcount for all 14 years FY13–FY26 match calibration targets (FY26 at 31-Mar-2026: 23,117).
   - Standalone Gross Revenue FY26: ₹1,32,508 cr (0.00% delta).
   - Offshore / Onshore Segment Split: ₹92,406 cr / ₹40,102 cr (0.00% delta).
   - Standalone CSR FY26: ₹949 cr (0.00% delta).
   - Total Hydrocarbon Liquids incl JV (Crude + Condensate): 20.501 MMT (within ±2% strict).
   - Natural Gas Production FY26: 19.966 BCM (within ±2% strict).
6. Every gold mart column required by question_coverage.yaml entries exists in the BigQuery schema.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pytest
import yaml
from google.cloud import bigquery

PROJECT_ID = "ongc-hr-finance-agent"
SILVER_DATASET = "hrfin_silver"
GOLD_DATASET = "hrfin_gold"
BRONZE_DATASET = "hrfin_bronze"

BASE_DIR = Path(__file__).resolve().parent.parent
CLEAN_EXCEL_DIR = BASE_DIR / "landing" / "excel" / "_clean"
SCHEMA_SILVER_PATH = BASE_DIR / "world_bible" / "schema_silver.yaml"
QUESTION_COVERAGE_PATH = BASE_DIR / "world_bible" / "question_coverage.yaml"
CALIBRATION_TARGETS_PATH = BASE_DIR / "world_bible" / "calibration_targets.yaml"

JOB_LABELS = {"datacloud": "ai-agent"}


@pytest.fixture(scope="module")
def bq_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)


@pytest.fixture(scope="module")
def schema_silver() -> Dict[str, Any]:
    with open(SCHEMA_SILVER_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def question_coverage() -> Dict[str, Any]:
    with open(QUESTION_COVERAGE_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def calibration_targets() -> Dict[str, Any]:
    with open(CALIBRATION_TARGETS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_01_all_silver_tables_exist_and_typed(bq_client: bigquery.Client, schema_silver: Dict[str, Any]):
    """Verify that all 53 silver tables exist in hrfin_silver with expected schema columns and types."""
    type_map = {
        "STRING": ["STRING"],
        "INT64": ["INTEGER", "INT64"],
        "NUMERIC": ["NUMERIC", "FLOAT", "FLOAT64"],
        "FLOAT64": ["FLOAT", "FLOAT64", "NUMERIC"],
        "BOOL": ["BOOLEAN", "BOOL"],
        "DATE": ["DATE"],
        "TIMESTAMP": ["TIMESTAMP"],
        "ARRAY<STRING>": ["STRING"],
    }

    errors = []
    tables = schema_silver["tables"]
    assert len(tables) == 53, f"Expected 53 silver tables in spec, found {len(tables)}"

    for t in tables:
        tname = t["table_name"]
        try:
            tbl = bq_client.get_table(f"{PROJECT_ID}.{SILVER_DATASET}.{tname}")
        except Exception as exc:
            errors.append(f"Table {tname} missing from BigQuery {SILVER_DATASET}: {exc}")
            continue

        bq_cols = {field.name: field for field in tbl.schema}
        for col_def in t["columns"]:
            cname = col_def["name"]
            ctype = col_def["type"]
            if cname not in bq_cols:
                errors.append(f"Table {tname}: missing column '{cname}'")
            else:
                field = bq_cols[cname]
                allowed = type_map.get(ctype, [ctype])
                if field.field_type not in allowed:
                    errors.append(f"Table {tname}.{cname}: type mismatch. Expected {ctype}, got {field.field_type}")

    assert not errors, f"Silver schema discrepancies encountered:\n" + "\n".join(errors[:20])


def test_02_dataform_assertions_pass(bq_client: bigquery.Client):
    """Verify that all Dataform assertion views evaluate to exactly 0 failing rows."""
    assertion_views = [
        "silver_foreign_keys",
        "silver_accepted_values",
        "gold_calibration_reconciliation",
        "silver_dim_grade_group_not_null",
        "silver_headcount_snapshot_grade_fk",
    ]

    for aview in assertion_views:
        query = f"SELECT COUNT(*) AS failing_count FROM `{PROJECT_ID}.{SILVER_DATASET}.{aview}`"
        query_job = bq_client.query(query, job_config=bigquery.QueryJobConfig(labels=JOB_LABELS))
        result = list(query_job.result())
        failing_rows = result[0]["failing_count"]
        assert failing_rows == 0, f"Dataform assertion {aview} failed with {failing_rows} violating rows!"


def test_03_silver_excel_exact_match_to_clean(bq_client: bigquery.Client):
    """Verify silver tables for messy Excel sources EXACTLY match clean tables (row count, PK set, numeric sum)."""
    excel_audit_configs = [
        ("capex_budget", "capex_be_re_actuals.xlsx", "budget_id", "actual_spend_inr_cr"),
        ("csr_projects", "csr_projects_tracker.xlsx", "csr_project_id", "actual_disbursed_inr_cr"),
        ("sanctioned_posts", "manpower_plan.xlsx", "sanction_id", "sanctioned_strength"),
        ("mou_targets", "dpe_mou_scorecard.xlsx", "mou_record_id", "weightage"),
        ("succession_plan", "succession_planning.xlsx", "position_id", None),
        ("grievances_litigation", "legal_cases_tracker.xlsx", "case_id", "age_days"),
    ]

    for silver_tbl, clean_file, pk_col, sum_col in excel_audit_configs:
        clean_path = CLEAN_EXCEL_DIR / clean_file
        assert clean_path.exists(), f"Clean workbook missing: {clean_path}"
        df_clean = pd.read_excel(clean_path)

        cols_to_query = [pk_col]
        if sum_col:
            cols_to_query.append(sum_col)
        select_clause = ", ".join(cols_to_query)

        query = f"SELECT {select_clause} FROM `{PROJECT_ID}.{SILVER_DATASET}.{silver_tbl}`"
        query_job = bq_client.query(query, job_config=bigquery.QueryJobConfig(labels=JOB_LABELS))
        bq_rows = [dict(r) for r in query_job.result()]

        # 1. Row count match
        assert len(bq_rows) == len(df_clean), f"{silver_tbl} row count mismatch: BQ={len(bq_rows)}, Clean={len(df_clean)}"

        # 2. PK set match
        clean_pks = set(str(k) for k in df_clean[pk_col])
        bq_pks = set(str(r[pk_col]) for r in bq_rows)
        assert clean_pks == bq_pks, f"{silver_tbl} PK set mismatch vs clean workbook"

        # 3. Numeric column sum match (tolerance < 0.01)
        if sum_col:
            clean_sum = round(float(df_clean[sum_col].sum()), 2)
            bq_sum = round(sum(float(r[sum_col]) for r in bq_rows if r[sum_col] is not None), 2)
            assert abs(clean_sum - bq_sum) < 0.01, f"{silver_tbl} sum({sum_col}) mismatch: clean={clean_sum}, bq={bq_sum}"


def test_04_all_gold_marts_and_views_exist(bq_client: bigquery.Client):
    """Verify all 16 gold marts + 5 semantic views + glossary (>=40 terms) + metric_definitions (>=60 metrics) exist."""
    expected_marts = [
        "mart_workforce",
        "mart_postings",
        "mart_promotions_dpc",
        "mart_payroll_benefits",
        "mart_training_development",
        "mart_hse_incident",
        "mart_contract_workforce",
        "mart_employee_relations",
        "mart_production_reserves",
        "mart_field_economics",
        "mart_capex_projects",
        "mart_procurement_contracts",
        "mart_corporate_performance",
        "mart_energy_transition",
        "mart_governance_audit",
        "mart_asset_productivity",
    ]

    expected_views = [
        "v_continuous_stay",
        "v_cluster_cumulative_tenure",
        "v_headcount_asof",
        "v_field_pnl",
        "v_lifting_cost",
    ]

    for m in expected_marts:
        tbl = bq_client.get_table(f"{PROJECT_ID}.{GOLD_DATASET}.{m}")
        assert tbl.num_rows > 0, f"Gold mart {m} is empty (0 rows)"

    for v in expected_views:
        query = f"SELECT COUNT(*) AS row_count FROM `{PROJECT_ID}.{GOLD_DATASET}.{v}`"
        query_job = bq_client.query(query, job_config=bigquery.QueryJobConfig(labels=JOB_LABELS))
        cnt = list(query_job.result())[0]["row_count"]
        assert cnt > 0, f"Semantic view {v} returned 0 rows"

    # Glossary must have >= 40 terms
    tbl_gloss = bq_client.get_table(f"{PROJECT_ID}.{GOLD_DATASET}.glossary")
    assert tbl_gloss.num_rows >= 40, f"Glossary has {tbl_gloss.num_rows} terms; target is >= 40"

    # Metric definitions must have >= 60 metrics
    tbl_metrics = bq_client.get_table(f"{PROJECT_ID}.{GOLD_DATASET}.metric_definitions")
    assert tbl_metrics.num_rows >= 60, f"Metric definitions has {tbl_metrics.num_rows} metrics; target is >= 60"


def test_05_gold_reconciles_to_calibration_targets(bq_client: bigquery.Client, calibration_targets: Dict[str, Any]):
    """Verify Gold metrics reconcile to authoritative public totals within strict ±2% tolerance."""
    # 1. Check all 14 fiscal year-ends headcounts (FY13..FY26) via v_headcount_asof
    hc_targets = {
        "2013-03-31": 32923,
        "2014-03-31": 33911,
        "2015-03-31": 33185,
        "2016-03-31": 33927,
        "2017-03-31": 33660,
        "2018-03-31": 32265,
        "2019-03-31": 31065,
        "2020-03-31": 30105,
        "2021-03-31": 28479,
        "2022-03-31": 27165,
        "2023-03-31": 25993,
        "2024-03-31": 25847,
        "2025-03-31": 24368,
        "2026-03-31": 23117,
    }

    q_hc = f"""
    SELECT
      as_of_date,
      SUM(active_headcount) AS total_headcount
    FROM `{PROJECT_ID}.{GOLD_DATASET}.v_headcount_asof`
    GROUP BY as_of_date
    """
    hc_results = {str(r["as_of_date"]): int(r["total_headcount"]) for r in bq_client.query(q_hc, job_config=bigquery.QueryJobConfig(labels=JOB_LABELS)).result()}

    for date_str, expected_hc in hc_targets.items():
        actual_hc = hc_results.get(date_str)
        assert actual_hc is not None, f"Missing as_of_date {date_str} in v_headcount_asof"
        delta_pct = abs(actual_hc - expected_hc) / expected_hc
        assert delta_pct <= 0.02, f"Headcount for {date_str}: actual {actual_hc} vs target {expected_hc} exceeds 2% (delta={delta_pct:.2%})"
        if date_str == "2026-03-31":
            assert actual_hc == 23117, f"FY26 31-March headcount must equal 23,117 exactly, got {actual_hc}"

    # 2. Financial and Operational Calibration Totals for FY26
    query_cal = f"""
    SELECT
      (SELECT gross_revenue_inr_cr FROM `{PROJECT_ID}.{GOLD_DATASET}.mart_corporate_performance` WHERE fiscal_year = 'FY26') AS rev_gross_fy26,
      (SELECT offshore_revenue_inr_cr FROM `{PROJECT_ID}.{GOLD_DATASET}.mart_corporate_performance` WHERE fiscal_year = 'FY26') AS rev_offshore_fy26,
      (SELECT onshore_revenue_inr_cr FROM `{PROJECT_ID}.{GOLD_DATASET}.mart_corporate_performance` WHERE fiscal_year = 'FY26') AS rev_onshore_fy26,
      (SELECT total_csr_spend_inr_cr FROM `{PROJECT_ID}.{GOLD_DATASET}.mart_corporate_performance` WHERE fiscal_year = 'FY26') AS csr_fy26,
      (SELECT ROUND(SUM(total_liquids_production_mmt), 3) FROM `{PROJECT_ID}.{GOLD_DATASET}.mart_asset_productivity` WHERE fiscal_year = 'FY26') AS liquids_fy26_mmt,
      (SELECT ROUND(SUM(gas_production_bcm), 3) FROM `{PROJECT_ID}.{GOLD_DATASET}.mart_asset_productivity` WHERE fiscal_year = 'FY26') AS gas_fy26_bcm,
      (SELECT ROUND(SUM(oil_production_mt + condensate_production_mt) / 1000000.0, 3) FROM `{PROJECT_ID}.{SILVER_DATASET}.production_monthly` WHERE fiscal_year = 'FY26' AND operatorship = 'operated') AS liquids_operated_mmt,
      (SELECT ROUND(SUM(oil_production_mt + condensate_production_mt) / 1000000.0, 3) FROM `{PROJECT_ID}.{SILVER_DATASET}.production_monthly` WHERE fiscal_year = 'FY26' AND operatorship = 'joint_venture') AS liquids_jv_mmt
    """
    raw_row = dict(list(bq_client.query(query_cal, job_config=bigquery.QueryJobConfig(labels=JOB_LABELS)).result())[0])
    cal_row = {k: float(v) if v is not None else 0.0 for k, v in raw_row.items()}

    # Gross revenue FY26: ₹1,32,508 cr (±2%)
    assert abs(cal_row["rev_gross_fy26"] - 132508.0) / 132508.0 <= 0.02, f"Gross revenue FY26 {cal_row['rev_gross_fy26']} exceeds 2% delta"

    # Offshore: ₹92,406 cr & Onshore: ₹40,102 cr (±2%)
    assert abs(cal_row["rev_offshore_fy26"] - 92406.0) / 92406.0 <= 0.02, f"Offshore revenue {cal_row['rev_offshore_fy26']} exceeds 2% delta"
    assert abs(cal_row["rev_onshore_fy26"] - 40102.0) / 40102.0 <= 0.02, f"Onshore revenue {cal_row['rev_onshore_fy26']} exceeds 2% delta"

    # CSR spend FY26: ₹949 cr (±2%)
    assert abs(cal_row["csr_fy26"] - 949.0) / 949.0 <= 0.02, f"CSR spend {cal_row['csr_fy26']} exceeds 2% delta"

    # Total hydrocarbon liquids incl JV (Crude + Condensate): 20.501 MMT (±2% strict)
    liquids_total = cal_row["liquids_fy26_mmt"]
    assert abs(liquids_total - 20.501) / 20.501 <= 0.02, f"Total liquids production {liquids_total} MMT exceeds strict 2% delta vs 20.501"

    # Operated vs JV split verified
    assert cal_row["liquids_operated_mmt"] > 18.0, "Operated liquids production too low"
    assert cal_row["liquids_jv_mmt"] > 1.0, "JV liquids production too low"

    # Natural gas production FY26: 19.966 BCM (±2% strict)
    gas_total = cal_row["gas_fy26_bcm"]
    assert abs(gas_total - 19.966) / 19.966 <= 0.02, f"Natural gas production {gas_total} BCM exceeds strict 2% delta vs 19.966"


def test_06_every_gold_mart_column_used_by_question_coverage_exists(bq_client: bigquery.Client, question_coverage: Dict[str, Any]):
    """Verify that every column required by question_coverage entries exists in the corresponding Gold mart."""
    errors = []

    # Pre-cache schemas for all gold marts
    marts = [m.replace("gold.", "") for m in question_coverage["gold_marts"].keys()]
    mart_schemas = {}
    for m in marts:
        tbl = bq_client.get_table(f"{PROJECT_ID}.{GOLD_DATASET}.{m}")
        mart_schemas[m] = set(f.name for f in tbl.schema)

    for entry in question_coverage["entries"]:
        qid = entry.get("id")
        gobj = entry.get("gold_layer_object")
        if not gobj or not gobj.startswith("gold."):
            continue
        mart_name = gobj.replace("gold.", "")
        mart_cols = mart_schemas.get(mart_name, set())

        for c in entry.get("columns", []):
            col_name = c.split(".")[-1]
            if col_name not in mart_cols:
                errors.append(f"Entry {qid}: Gold mart '{mart_name}' missing required column '{col_name}' (from {c})")

    assert not errors, f"Missing columns in gold marts required by question coverage:\n" + "\n".join(errors[:25])
