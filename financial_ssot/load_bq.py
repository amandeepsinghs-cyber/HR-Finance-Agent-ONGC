"""Reproducible BigQuery staging-to-gold loader for Yukti v3 Financial SSOT (Packet P1.6 Part A.3, I3).

Workflow:
1. Create schemas `hrfin_bronze`, `hrfin_gold_staging`, `hrfin_gold` if not exists (additive only; never touches `ssot_corporate_*`).
2. Load `fin_extract_raw.parquet` to `hrfin_bronze.fin_extract_raw`.
3. Load `dim_financial_line.csv`, `fact_financial_statement_line.parquet`, `conflicts.csv`, `fin_gate_run.parquet`,
   and the 5 P1.7 anchor tables (`fact_segment`, `fact_production_annual`, `fact_reserves`, `fact_hr_aggregates`,
   `fact_price_realisation`) into `hrfin_gold_staging` first (partitioned/clustered per SPEC-01 §5.4).
4. Create staging views (`v_fin_statement_as_reported`, `v_fin_trend_latest`, `v_fin_quarterly_xbrl`,
   `v_fin_opening_bs`, `v_fin_yahoo_view`, `v_fin_coverage`) in `hrfin_gold_staging`.
5. Run BigQuery-side verification queries on `hrfin_gold_staging`:
   - Compare row counts, verified counts, and gate failure counts against offline artifacts.
   - Verify 0 duplicate `(fiscal_year, scope, line_code)` keys in both `v_fin_statement_as_reported` and `v_fin_trend_latest`.
   - Verify 0 `resolved` conflict rows with `resolved_by IS NULL`.
6. Promote verified staging tables to `hrfin_gold` and recreate serving views in `hrfin_gold`.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

SSOT_DIR = Path(__file__).resolve().parent
OUT_DIR = SSOT_DIR / "out"
DIM_CSV_PATH = SSOT_DIR / "dim_financial_line.csv"

PROJECT_ID = "ongc-hr-finance-agent"
LOCATION = "asia-south1"
BRONZE_DS = "hrfin_bronze"
STAGING_DS = "hrfin_gold_staging"
GOLD_DS = "hrfin_gold"
LABEL = "datacloud:antigravity"


def _bq_query(sql: str) -> List[Dict[str, Any]]:
    cmd = [
        "bq",
        f"--project_id={PROJECT_ID}",
        f"--location={LOCATION}",
        "query",
        "--use_legacy_sql=false",
        "--format=json",
        "--max_rows=10000",
        "--label",
        LABEL,
        sql,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"bq query failed ({proc.returncode}):\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}\nSQL:\n{sql}")
    out = proc.stdout.strip()
    if not out or out == "[]":
        return []
    # bq sometimes emits status lines before JSON when DDL runs; locate '[' if present
    idx = out.find("[")
    if idx == -1:
        return []
    return json.loads(out[idx:])


def _bq_load_parquet(
    parquet_path: Path,
    dataset: str,
    table: str,
    time_partitioning_field: str | None = None,
    time_partitioning_type: str = "YEAR",
    clustering_fields: str | None = None,
) -> None:
    cmd = [
        "bq",
        f"--project_id={PROJECT_ID}",
        f"--location={LOCATION}",
        "load",
        "--replace",
        "--source_format=PARQUET",
        "--label",
        LABEL,
    ]
    if time_partitioning_field:
        cmd.extend([f"--time_partitioning_field={time_partitioning_field}", f"--time_partitioning_type={time_partitioning_type}"])
    if clustering_fields:
        cmd.append(f"--clustering_fields={clustering_fields}")
    cmd.extend([f"{PROJECT_ID}:{dataset}.{table}", str(parquet_path)])
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"bq load failed for {dataset}.{table}:\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}")


def _bq_cp_promote(src_ds: str, dst_ds: str, table: str) -> None:
    cmd = [
        "bq",
        f"--project_id={PROJECT_ID}",
        f"--location={LOCATION}",
        "cp",
        "-f",
        "--label",
        LABEL,
        f"{PROJECT_ID}:{src_ds}.{table}",
        f"{PROJECT_ID}:{dst_ds}.{table}",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"bq cp failed for {src_ds}.{table} -> {dst_ds}.{table}:\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}")


def _create_views(ds: str) -> None:
    views_sql = f"""
    CREATE OR REPLACE VIEW `{PROJECT_ID}.{ds}.v_fin_statement_as_reported` AS
    SELECT
      f.*,
      d.display_name,
      d.line_name,
      d.section,
      d.subsection,
      d.level,
      d.hierarchy_level,
      d.display_order,
      d.line_kind,
      d.line_class,
      d.subtotal_formula,
      d.formula,
      d.sign_in_parent,
      d.natural_sign,
      d.schedule3_ref,
      d.ar_note_ref_typical,
      d.xbrl_element_name,
      d.yahoo_field_name,
      d.scope_applicability,
      d.unit_default,
      d.is_subtotal,
      d.is_total,
      d.is_kpi
    FROM `{PROJECT_ID}.{ds}.fact_financial_statement_line` f
    JOIN `{PROJECT_ID}.{ds}.dim_financial_line` d
      USING (line_code)
    WHERE f.verified = TRUE
      AND f.period_type = 'annual'
      AND f.is_own_vintage = TRUE
      AND (f.source_system = 'ar' OR f.fiscal_year = 'FY20');

    CREATE OR REPLACE VIEW `{PROJECT_ID}.{ds}.v_fin_trend_latest` AS
    SELECT
      f.*,
      d.display_name,
      d.line_name,
      d.section,
      d.subsection,
      d.level,
      d.hierarchy_level,
      d.display_order,
      d.line_kind,
      d.line_class,
      d.subtotal_formula,
      d.formula,
      d.sign_in_parent,
      d.natural_sign,
      d.schedule3_ref,
      d.ar_note_ref_typical,
      d.xbrl_element_name,
      d.yahoo_field_name,
      d.scope_applicability,
      d.unit_default,
      d.is_subtotal,
      d.is_total,
      d.is_kpi,
      CASE
        WHEN f.is_restated THEN CONCAT(f.fiscal_year, ' restated in ', f.report_vintage)
        ELSE NULL
      END AS footnote_marker
    FROM `{PROJECT_ID}.{ds}.fact_financial_statement_line` f
    JOIN `{PROJECT_ID}.{ds}.dim_financial_line` d
      USING (line_code)
    WHERE f.verified = TRUE
      AND f.period_type = 'annual'
      AND f.is_latest_vintage = TRUE;

    CREATE OR REPLACE VIEW `{PROJECT_ID}.{ds}.v_fin_quarterly_xbrl` AS
    SELECT
      f.*,
      d.display_name,
      d.line_name,
      d.section,
      d.subsection,
      d.level,
      d.line_kind,
      d.unit_default,
      d.is_kpi
    FROM `{PROJECT_ID}.{ds}.fact_financial_statement_line` f
    JOIN `{PROJECT_ID}.{ds}.dim_financial_line` d
      USING (line_code)
    WHERE f.verified = TRUE
      AND f.period_type = 'quarter';

    CREATE OR REPLACE VIEW `{PROJECT_ID}.{ds}.v_fin_opening_bs` AS
    SELECT
      f.*,
      d.display_name,
      d.line_name,
      d.section,
      d.subsection,
      d.level,
      d.line_kind,
      d.unit_default,
      d.is_kpi
    FROM `{PROJECT_ID}.{ds}.fact_financial_statement_line` f
    JOIN `{PROJECT_ID}.{ds}.dim_financial_line` d
      USING (line_code)
    WHERE f.verified = TRUE
      AND f.period_type = 'opening';

    CREATE OR REPLACE VIEW `{PROJECT_ID}.{ds}.v_fin_yahoo_view` AS
    SELECT
      f.fiscal_year,
      f.period_type,
      f.period_end,
      f.scope,
      f.statement,
      f.line_code,
      d.display_name,
      d.line_name,
      d.yahoo_field_name,
      f.value_inr_cr,
      f.value,
      f.unit,
      f.report_vintage,
      f.source_doc,
      f.source_page
    FROM `{PROJECT_ID}.{ds}.fact_financial_statement_line` f
    JOIN `{PROJECT_ID}.{ds}.dim_financial_line` d
      USING (line_code)
    WHERE f.verified = TRUE
      AND f.source_system = 'yahoo'
      AND f.scope = 'consolidated';

    CREATE OR REPLACE VIEW `{PROJECT_ID}.{ds}.v_fin_coverage` AS
    SELECT
      f.fiscal_year,
      f.scope,
      f.statement,
      f.source_system,
      COUNT(*) AS total_lines,
      COUNT(DISTINCT f.line_code) AS distinct_lines,
      COUNTIF(f.verified) AS verified_lines,
      COUNTIF(f.verified AND d.is_kpi) AS verified_kpi_lines,
      COUNTIF(f.is_restated) AS restated_lines,
      MIN(f.report_vintage) AS earliest_vintage,
      MAX(f.report_vintage) AS latest_vintage
    FROM `{PROJECT_ID}.{ds}.fact_financial_statement_line` f
    LEFT JOIN `{PROJECT_ID}.{ds}.dim_financial_line` d
      USING (line_code)
    GROUP BY 1, 2, 3, 4;
    """
    _bq_query(views_sql)


def run_staging_and_promote() -> Dict[str, Any]:
    # 1. Ensure datasets exist
    _bq_query(
        f"""
        CREATE SCHEMA IF NOT EXISTS `{PROJECT_ID}.{BRONZE_DS}`
          OPTIONS(location="{LOCATION}", description="Yukti v3 Financial SSOT Bronze landing tables");
        CREATE SCHEMA IF NOT EXISTS `{PROJECT_ID}.{STAGING_DS}`
          OPTIONS(location="{LOCATION}", description="Yukti v3 Financial SSOT Gold staging dataset");
        CREATE SCHEMA IF NOT EXISTS `{PROJECT_ID}.{GOLD_DS}`
          OPTIONS(location="{LOCATION}", description="Yukti v3 Financial SSOT Verified Gold dataset");
        """
    )

    dim_df = pd.read_csv(DIM_CSV_PATH)
    fact_df = pd.read_parquet(OUT_DIR / "fact_financial_statement_line.parquet")
    conflicts_df = pd.read_csv(OUT_DIR / "conflicts.csv")
    gates_df = pd.read_parquet(OUT_DIR / "fin_gate_run.parquet")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Write dim_financial_line and conflicts with explicit string types so null columns don't become null-type in Parquet
        dim_pq = tmp_path / "dim_financial_line.parquet"
        for col in dim_df.columns:
            if dim_df[col].dtype == object:
                dim_df[col] = dim_df[col].where(dim_df[col].notna(), None).astype("string")
        dim_df.to_parquet(dim_pq, index=False)

        conf_pq = tmp_path / "fact_financial_line_conflict.parquet"
        str_cols_conf = [
            "fiscal_year",
            "scope",
            "line_code",
            "source_a",
            "source_b",
            "rule_id",
            "status",
            "resolution_rule",
            "resolution",
            "resolved_by",
            "resolved_at",
        ]
        for col in str_cols_conf:
            if col in conflicts_df.columns:
                conflicts_df[col] = conflicts_df[col].where(conflicts_df[col].notna(), None).astype("string")
        conflicts_df.to_parquet(conf_pq, index=False)

        # 2. Load Bronze
        _bq_load_parquet(OUT_DIR / "fin_extract_raw.parquet", BRONZE_DS, "fin_extract_raw")

        # Prepare fact_financial_statement_line with DATE period_end
        fact_pq = tmp_path / "fact_financial_statement_line.parquet"
        fact_copy = fact_df.copy()
        fact_copy["period_end"] = pd.to_datetime(fact_copy["period_end"]).dt.date
        fact_copy.to_parquet(fact_pq, index=False)

        # 3. Load Staging tables
        _bq_load_parquet(dim_pq, STAGING_DS, "dim_financial_line", clustering_fields="statement,section")
        _bq_load_parquet(
            fact_pq,
            STAGING_DS,
            "fact_financial_statement_line",
            time_partitioning_field="period_end",
            time_partitioning_type="YEAR",
            clustering_fields="scope,statement,line_code",
        )
        _bq_load_parquet(conf_pq, STAGING_DS, "fact_financial_line_conflict", clustering_fields="fiscal_year,scope,line_code")
        _bq_load_parquet(OUT_DIR / "fin_gate_run.parquet", STAGING_DS, "fin_gate_run")

        # Load the 5 P1.7 anchor tables into staging
        anchor_names = [
            "fact_segment",
            "fact_production_annual",
            "fact_reserves",
            "fact_hr_aggregates",
            "fact_price_realisation",
        ]
        for aname in anchor_names:
            apath = OUT_DIR / f"{aname}.parquet"
            if apath.exists():
                _bq_load_parquet(apath, STAGING_DS, aname)

        # 4. Create views in staging
        _create_views(STAGING_DS)

        # 5. Run BigQuery verification assertions on hrfin_gold_staging
        stg_summary = _bq_query(
            f"""
            SELECT
              COUNT(*) AS total_rows,
              COUNTIF(verified) AS verified_rows,
              COUNTIF(is_own_vintage) AS own_rows,
              COUNTIF(is_fallback_vintage) AS fallback_rows,
              COUNTIF(is_latest_vintage) AS latest_rows,
              COUNTIF(is_restated) AS restated_rows,
              COUNTIF(NOT v02_no_plugs_ok) AS v02_fails,
              COUNTIF(NOT v03_bs_identity) AS v03_fails,
              COUNTIF(NOT v04_cash_tie) AS v04_fails
            FROM `{PROJECT_ID}.{STAGING_DS}.fact_financial_statement_line`
            """
        )[0]

        assert int(stg_summary["total_rows"]) == len(fact_df), f"Staging row mismatch: {stg_summary['total_rows']} != {len(fact_df)}"
        assert int(stg_summary["verified_rows"]) == int(fact_df["verified"].sum()), "Staging verified count mismatch"
        assert int(stg_summary["v02_fails"]) == 0, "V02 plug check failed in staging"
        assert int(stg_summary["v03_fails"]) == 0, "V03 BS identity check failed in staging"
        assert int(stg_summary["v04_fails"]) == 0, "V04 cash tie check failed in staging"

        dup_as_rep = _bq_query(
            f"""
            SELECT fiscal_year, scope, line_code, COUNT(*) AS c
            FROM `{PROJECT_ID}.{STAGING_DS}.v_fin_statement_as_reported`
            GROUP BY 1, 2, 3
            HAVING COUNT(*) > 1
            """
        )
        dup_trend = _bq_query(
            f"""
            SELECT fiscal_year, scope, line_code, COUNT(*) AS c
            FROM `{PROJECT_ID}.{STAGING_DS}.v_fin_trend_latest`
            GROUP BY 1, 2, 3
            HAVING COUNT(*) > 1
            """
        )
        assert len(dup_as_rep) == 0, f"Duplicate keys in staging v_fin_statement_as_reported: {dup_as_rep}"
        assert len(dup_trend) == 0, f"Duplicate keys in staging v_fin_trend_latest: {dup_trend}"

        bad_resolved = _bq_query(
            f"""
            SELECT COUNT(*) AS bad_n
            FROM `{PROJECT_ID}.{STAGING_DS}.fact_financial_line_conflict`
            WHERE status = 'resolved' AND (resolved_by IS NULL OR resolved_at IS NULL)
            """
        )[0]
        assert int(bad_resolved["bad_n"]) == 0, "Found resolved conflicts with NULL resolved_by/resolved_at in staging"

        # 6. Promote verified staging tables to hrfin_gold (WRITE_TRUNCATE of v3 tables)
        _bq_load_parquet(dim_pq, GOLD_DS, "dim_financial_line", clustering_fields="statement,section")
        _bq_load_parquet(
            fact_pq,
            GOLD_DS,
            "fact_financial_statement_line",
            time_partitioning_field="period_end",
            time_partitioning_type="DAY",
            clustering_fields="scope,statement,fiscal_year,line_code",
        )
        _bq_load_parquet(conf_pq, GOLD_DS, "fact_financial_line_conflict", clustering_fields="fiscal_year,scope,line_code")
        _bq_load_parquet(OUT_DIR / "fin_gate_run.parquet", GOLD_DS, "fin_gate_run")
        for aname in anchor_names:
            apath = OUT_DIR / f"{aname}.parquet"
            if apath.exists():
                _bq_load_parquet(apath, GOLD_DS, aname)

    _create_views(GOLD_DS)

    counts_rows = _bq_query(
        f"""
        SELECT 'bronze.fin_extract_raw' AS tbl, COUNT(*) AS n FROM `{PROJECT_ID}.{BRONZE_DS}.fin_extract_raw`
        UNION ALL SELECT 'gold.dim_financial_line', COUNT(*) FROM `{PROJECT_ID}.{GOLD_DS}.dim_financial_line`
        UNION ALL SELECT 'gold.fact_financial_statement_line', COUNT(*) FROM `{PROJECT_ID}.{GOLD_DS}.fact_financial_statement_line`
        UNION ALL SELECT 'gold.fact_financial_line_conflict', COUNT(*) FROM `{PROJECT_ID}.{GOLD_DS}.fact_financial_line_conflict`
        UNION ALL SELECT 'gold.fin_gate_run', COUNT(*) FROM `{PROJECT_ID}.{GOLD_DS}.fin_gate_run`
        UNION ALL SELECT 'gold.fact_segment', COUNT(*) FROM `{PROJECT_ID}.{GOLD_DS}.fact_segment`
        UNION ALL SELECT 'gold.fact_production_annual', COUNT(*) FROM `{PROJECT_ID}.{GOLD_DS}.fact_production_annual`
        UNION ALL SELECT 'gold.fact_reserves', COUNT(*) FROM `{PROJECT_ID}.{GOLD_DS}.fact_reserves`
        UNION ALL SELECT 'gold.fact_hr_aggregates', COUNT(*) FROM `{PROJECT_ID}.{GOLD_DS}.fact_hr_aggregates`
        UNION ALL SELECT 'gold.fact_price_realisation', COUNT(*) FROM `{PROJECT_ID}.{GOLD_DS}.fact_price_realisation`
        ORDER BY 1
        """
    )
    result = {
        "staging_summary": stg_summary,
        "dup_keys_v_fin_statement_as_reported": len(dup_as_rep),
        "dup_keys_v_fin_trend_latest": len(dup_trend),
        "promoted_table_counts": {r["tbl"]: int(r["n"]) for r in counts_rows},
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    run_staging_and_promote()
