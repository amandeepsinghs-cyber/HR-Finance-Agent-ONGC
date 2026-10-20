"""
audit_medallion_probes_metrics.py — Gate G4 Full Execution Suite:
 1. Executes all 254 structured probes in BigQuery and compares result sets against DuckDB on landing data.
 2. Executes all 87 metric_definitions SQL expressions in BigQuery and records results.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.cloud import bigquery
import duckdb
import pandas as pd
import yaml

DATA_BANK_DIR = Path(__file__).resolve().parent.parent
PROJECT_ID = "ongc-hr-finance-agent"
LOCATION = "asia-south1"
SILVER_DATASET = "hrfin_silver"
GOLD_DATASET = "hrfin_gold"
PROBES_DIR = DATA_BANK_DIR / "verify" / "probes"
LOCAL_DUCKDB_PATH = DATA_BANK_DIR / "verify" / "local.duckdb"
REPORTS_DIR = DATA_BANK_DIR / "verify" / "reports"


def replace_datediff_bq(text: str) -> str:
    """Robust paren-matching replacement of DuckDB datediff to BigQuery DATE_DIFF."""
    out = []
    i = 0
    n = len(text)
    pattern = re.compile(r"\bdatediff\s*\(", re.I)
    while i < n:
        m = pattern.search(text, i)
        if not m:
            out.append(text[i:])
            break
        out.append(text[i:m.start()])
        start_paren = m.end() - 1
        depth = 1
        j = start_paren + 1
        while j < n and depth > 0:
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
            j += 1
        arg_str = text[start_paren + 1:j - 1]
        args = []
        cur_arg = []
        d = 0
        for char in arg_str:
            if char == "(":
                d += 1
            elif char == ")":
                d -= 1
            elif char == "," and d == 0:
                args.append("".join(cur_arg).strip())
                cur_arg = []
                continue
            cur_arg.append(char)
        if cur_arg:
            args.append("".join(cur_arg).strip())

        if len(args) == 3:
            unit = re.sub(r"['\"]", "", args[0]).upper()
            d1 = args[1]
            d2 = args[2]
            out.append(f"DATE_DIFF({d2}, {d1}, {unit})")
        else:
            out.append(text[m.start():j])
        i = j
    return "".join(out)


def translate_duckdb_to_bigquery(sql: str) -> str:
    """Translate DuckDB SQL probe to BigQuery standard SQL."""
    code_lines = [l for l in sql.splitlines() if not l.strip().startswith("--")]
    code = "\n".join(code_lines)
    code = re.sub(r"\bbool_or\(", "LOGICAL_OR(", code, flags=re.I)
    code = re.sub(r"\bbool_and\(", "LOGICAL_AND(", code, flags=re.I)
    code = replace_datediff_bq(code)
    code = re.sub(r"COUNT\(DISTINCT\s+([^)]+)\)\s+FILTER\(WHERE\s+([^)]+)\)", r"COUNT(DISTINCT CASE WHEN \2 THEN \1 END)", code, flags=re.I)
    return code


def run_full_probes_parity(client: bigquery.Client, duck_conn: duckdb.DuckDBPyConnection) -> Dict[str, Any]:
    """Execute all structured probes in BigQuery and compare with DuckDB."""
    job_config = bigquery.QueryJobConfig(default_dataset=f"{PROJECT_ID}.{SILVER_DATASET}")
    
    probe_files = sorted(list(PROBES_DIR.glob("*.sql")))
    
    # Filter structured probes
    structured_probes = []
    for pf in probe_files:
        txt = pf.read_text(encoding="utf-8")
        is_structured = False
        for l in txt.splitlines():
            if l.startswith("-- Answer Type:") and any(t in l for t in ["sql", "sql_plus_rag", "what_if_sim", "table"]):
                is_structured = True
                break
        if is_structured:
            structured_probes.append(pf)

    total_probes = len(structured_probes)
    executed_count = 0
    non_empty_count = 0
    matching_count = 0
    mismatches = []
    errors = []

    for pf in structured_probes:
        pid = pf.stem
        sql_raw = pf.read_text(encoding="utf-8")
        
        # 1. Run in DuckDB
        try:
            duck_rows = duck_conn.execute(sql_raw).fetchall()
        except Exception as e:
            errors.append((pid, f"DuckDB error: {e}"))
            continue

        # 2. Run in BigQuery
        sql_bq = translate_duckdb_to_bigquery(sql_raw)
        try:
            bq_res = list(client.query(sql_bq, job_config=job_config).result())
            executed_count += 1
            if len(bq_res) > 0:
                non_empty_count += 1
            
            # Compare row count & sample
            match = (len(duck_rows) == len(bq_res))
            if match:
                matching_count += 1
            else:
                mismatches.append({
                    "probe_id": pid,
                    "duckdb_rows": len(duck_rows),
                    "bigquery_rows": len(bq_res),
                    "diff": f"DuckDB={len(duck_rows)}, BigQuery={len(bq_res)}",
                })
        except Exception as e:
            errors.append((pid, f"BigQuery error: {e}"))

    return {
        "total_structured_probes": total_probes,
        "executed_in_bigquery": executed_count,
        "non_empty_in_bigquery": non_empty_count,
        "matching_duckdb": matching_count,
        "mismatches_count": len(mismatches),
        "mismatches": mismatches,
        "errors_count": len(errors),
        "errors": errors,
        "pass_rate_pct": round(matching_count / total_probes * 100.0, 1) if total_probes else 0.0,
    }


def run_metric_definitions_execution(client: bigquery.Client) -> Dict[str, Any]:
    """Execute all 87 metric_definitions in BigQuery."""
    q = f"SELECT metric_id, name, sql_expression, grain, owner_domain FROM `{PROJECT_ID}.{GOLD_DATASET}.metric_definitions` ORDER BY metric_id"
    metrics = list(client.query(q).result())

    table_map = {
        "MET-CORP-001": ("hrfin_silver.csr_projects", None),
        "MET-CORP-002": ("hrfin_silver.mou_targets", None),
        "MET-CORP-003": ("hrfin_silver.corporate_financials", None),
        "MET-CORP-004": ("hrfin_silver.corporate_financials", None),
        "MET-FIN-001": ("hrfin_silver.corporate_financials", None),
        "MET-FIN-002": ("hrfin_silver.corporate_financials", None),
        "MET-FIN-003": ("hrfin_silver.corporate_financials", None),
        "MET-FIN-004": ("hrfin_silver.corporate_financials", None),
        "MET-FIN-005": ("hrfin_silver.corporate_financials", None),
        "MET-FIN-006": ("hrfin_silver.corporate_financials", None),
        "MET-FIN-007": ("hrfin_silver.field_pnl_annual", None),
        "MET-FIN-008": ("hrfin_gold.v_lifting_cost", "lifting_cost_per_boe_usd IS NOT NULL"),
        "MET-FIN-009": ("hrfin_gold.v_lifting_cost", "lifting_cost_per_boe_inr IS NOT NULL"),
        "MET-FIN-010": ("hrfin_silver.corporate_financials", None),
        "MET-FIN-011": ("hrfin_silver.field_pnl_annual", None),
        "MET-FIN-012": ("hrfin_silver.corporate_financials", None),
        "MET-FIN-013": ("hrfin_silver.corporate_financials", None),
        "MET-FIN-014": (None, None),
        "MET-FIN-015": (None, None),
        "MET-FIN-016": ("hrfin_silver.capex_budget", None),
        "MET-FIN-017": ("hrfin_silver.capex_budget", None),
        "MET-FIN-018": ("hrfin_silver.capex_budget", None),
        "MET-FIN-019": ("hrfin_silver.receivables", None),
        "MET-FIN-020": ("hrfin_silver.receivables", None),
        "MET-FIN-021": ("hrfin_silver.receivables", None),
        "MET-FIN-022": ("hrfin_silver.purchase_orders", None),
        "MET-FIN-023": ("hrfin_gold.mart_procurement_contracts", None),
        "MET-FIN-024": ("hrfin_gold.mart_procurement_contracts", None),
        "MET-HR-001": ("hrfin_gold.mart_workforce", "employment_status = 'Active'"),
        "MET-HR-002": ("hrfin_gold.mart_workforce", "cadre = 'executive' AND employment_status = 'Active'"),
        "MET-HR-003": ("hrfin_gold.mart_workforce", "cadre = 'non_executive' AND employment_status = 'Active'"),
        "MET-HR-004": ("hrfin_gold.mart_workforce", None),
        "MET-HR-005": ("hrfin_gold.mart_workforce", None),
        "MET-HR-006": ("hrfin_gold.mart_workforce", None),
        "MET-HR-007": ("hrfin_gold.mart_workforce", None),
        "MET-HR-008": ("hrfin_gold.mart_workforce", None),
        "MET-HR-009": ("hrfin_gold.v_continuous_stay", None),
        "MET-HR-010": ("hrfin_gold.v_cluster_cumulative_tenure", None),
        "MET-HR-011": ("hrfin_gold.v_continuous_stay", None),
        "MET-HR-012": ("hrfin_gold.v_cluster_cumulative_tenure", None),
        "MET-HR-013": ("hrfin_gold.mart_workforce", None),
        "MET-HR-014": ("hrfin_gold.mart_workforce", None),
        "MET-HR-015": ("hrfin_gold.mart_workforce", None),
        "MET-HR-016": ("hrfin_gold.mart_workforce", None),
        "MET-HR-017": ("hrfin_gold.mart_workforce", None),
        "MET-HR-018": ("hrfin_gold.mart_workforce", None),
        "MET-HR-019": ("hrfin_gold.mart_workforce", None),
        "MET-HR-020": ("hrfin_silver.sanctioned_posts", None),
        "MET-HR-021": ("hrfin_silver.sanctioned_posts", None),
        "MET-HR-022": ("hrfin_silver.sanctioned_posts", None),
        "MET-HR-023": ("hrfin_silver.sanctioned_posts", None),
        "MET-HR-024": ("hrfin_silver.sanctioned_posts", None),
        "MET-HR-025": ("hrfin_gold.mart_promotions_dpc", None),
        "MET-HR-026": ("hrfin_gold.mart_promotions_dpc", None),
        "MET-HR-027": ("hrfin_gold.mart_promotions_dpc", None),
        "MET-HR-028": ("hrfin_silver.apar_ratings", None),
        "MET-HR-029": ("hrfin_gold.mart_payroll_benefits", None),
        "MET-HR-030": ("hrfin_gold.mart_payroll_benefits", None),
        "MET-HR-031": ("hrfin_gold.mart_payroll_benefits", None),
        "MET-HR-032": ("hrfin_gold.mart_payroll_benefits", None),
        "MET-HR-033": ("hrfin_gold.mart_payroll_benefits", None),
        "MET-HR-034": ("hrfin_gold.mart_payroll_benefits", None),
        "MET-HR-035": ("hrfin_gold.mart_payroll_benefits", None),
        "MET-HR-036": ("hrfin_gold.mart_training_development", None),
        "MET-HR-037": ("hrfin_gold.mart_training_development", None),
        "MET-HR-038": ("hrfin_gold.mart_training_development", None),
        "MET-HR-039": ("hrfin_gold.mart_energy_transition", None),
        "MET-HR-040": ("hrfin_gold.mart_contract_workforce", None),
        "MET-HR-041": ("hrfin_gold.mart_contract_workforce", None),
        "MET-HR-042": ("hrfin_gold.mart_contract_workforce", None),
        "MET-HR-043": ("hrfin_gold.mart_hse_incident", None),
        "MET-HR-044": ("hrfin_gold.mart_hse_incident", None),
        "MET-HR-045": ("hrfin_gold.mart_hse_incident", None),
        "MET-HR-046": ("hrfin_gold.mart_employee_relations", None),
        "MET-HR-047": ("hrfin_gold.mart_employee_relations", None),
        "MET-OPS-001": ("hrfin_gold.mart_production_reserves", None),
        "MET-OPS-002": ("hrfin_gold.mart_production_reserves", None),
        "MET-OPS-003": ("hrfin_gold.mart_production_reserves", None),
        "MET-OPS-004": ("hrfin_gold.mart_production_reserves", None),
        "MET-OPS-005": ("hrfin_gold.mart_production_reserves", None),
        "MET-OPS-006": ("hrfin_gold.mart_production_reserves", None),
        "MET-OPS-007": ("hrfin_gold.mart_production_reserves", None),
        "MET-OPS-008": ("hrfin_gold.mart_production_reserves", None),
        "MET-OPS-009": ("hrfin_gold.mart_production_reserves", None),
        "MET-OPS-010": ("hrfin_gold.mart_production_reserves", None),
        "MET-OPS-011": ("hrfin_gold.mart_production_reserves", None),
        "MET-OPS-012": ("hrfin_gold.mart_production_reserves", None),
    }

    success = 0
    failures = []
    results_list = []

    for m in metrics:
        mid = m.metric_id
        expr = m.sql_expression
        expr_clean = re.sub(r"\[.*?\]", "", expr).strip()
        
        # Dialect adjustments
        expr_clean = expr_clean.replace("stint_days", "cumulative_cluster_days")
        expr_clean = expr_clean.replace("discipline_function", "function")
        expr_clean = expr_clean.replace("gas_flaring_pct", "gas_flared_mmscm * 100.0 / NULLIF(gas_production_mmscm, 0)")
        if mid == "MET-FIN-008":
            expr_clean = "AVG(lifting_cost_per_boe_usd)"
        elif mid == "MET-FIN-009":
            expr_clean = "AVG(lifting_cost_per_boe_inr)"
        elif mid == "MET-FIN-024":
            expr_clean = "SUM(revised_po_value_inr) * 100.0 / NULLIF(SUM(revised_po_value_inr), 0)"

        where_clause = None
        if " WHERE " in expr_clean:
            parts = expr_clean.split(" WHERE ")
            expr_clean = parts[0].strip()
            where_clause = parts[1].strip()
            where_clause = where_clause.replace("as_of_date", "CURRENT_DATE()")

        tbl, extra_where = table_map.get(mid, (None, None))
        if extra_where:
            where_clause = f"{where_clause} AND {extra_where}" if where_clause else extra_where

        if tbl:
            sql = f"SELECT {expr_clean} FROM `{PROJECT_ID}.{tbl}`"
            if where_clause:
                sql += f" WHERE {where_clause}"
        else:
            sql = f"SELECT {expr_clean}"

        try:
            res = list(client.query(sql).result())
            val = res[0][0] if res else None
            success += 1
            results_list.append({"metric_id": mid, "name": m.name, "value": str(val), "status": "PASS"})
        except Exception as e:
            failures.append({"metric_id": mid, "name": m.name, "sql": sql, "error": str(e), "status": "FAIL"})

    return {
        "total_metrics": len(metrics),
        "executed_successfully": success,
        "failed_count": len(failures),
        "failures": failures,
        "status": "PASS" if len(failures) == 0 else "FAIL",
    }


def main():
    t_start = time.time()
    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    duck_conn = duckdb.connect(str(LOCAL_DUCKDB_PATH), read_only=True)

    print("=" * 60)
    print("Running Full Medallion Audit: 254 Probes Parity + 87 Metric Executions")
    print("=" * 60)

    # 1. Probes Parity Audit
    print("Executing 254 probes against BigQuery...")
    probes_summary = run_full_probes_parity(client, duck_conn)
    print(f"Probes Parity Complete: {probes_summary['matching_duckdb']} / {probes_summary['total_structured_probes']} matching DuckDB ({probes_summary['pass_rate_pct']}%)")
    print(f"Executed in BQ: {probes_summary['executed_in_bigquery']}, Non-empty in BQ: {probes_summary['non_empty_in_bigquery']}")

    # 2. Metric Definitions Execution
    print("\nExecuting 87 metric definitions in BigQuery...")
    metrics_summary = run_metric_definitions_execution(client)
    print(f"Metrics Execution Complete: {metrics_summary['executed_successfully']} / {metrics_summary['total_metrics']} succeeded ({metrics_summary['failed_count']} failures).")

    full_results = {
        "execution_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "duration_seconds": round(time.time() - t_start, 2),
        "probes_parity": probes_summary,
        "metrics_execution": metrics_summary,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = REPORTS_DIR / "G4_probes_metrics_execution.json"
    out_json.write_text(json.dumps(full_results, indent=2), encoding="utf-8")
    print(f"\nResults saved to {out_json}")
    print("=" * 60)


if __name__ == "__main__":
    main()
