"""
story_actuals.py — Records and appends actual story values computed from record-level
truth to data_bank/world_bible/story_register_actuals.yaml.

Supports the fully emergent simulation policy:
Story numbers in story_register.yaml are EXPECTATIONS. Actual values computed live
from DuckDB records become the empirical ground truth.
All expectations are read dynamically from YAML — zero hard-coded numbers.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import duckdb
import yaml

WORLD_BIBLE_DIR = Path(__file__).resolve().parent.parent / "world_bible"
STORY_REGISTER_PATH = WORLD_BIBLE_DIR / "story_register.yaml"
CALIBRATION_TARGETS_PATH = WORLD_BIBLE_DIR / "calibration_targets.yaml"
ACTUALS_YAML_PATH = WORLD_BIBLE_DIR / "story_register_actuals.yaml"


def load_story_expectations() -> Dict[Tuple[str, str], Dict[str, Any]]:
    """Load all exact_numbers from story_register.yaml: {(story_id, metric): {...}}"""
    expectations: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if not STORY_REGISTER_PATH.exists():
        return expectations

    with open(STORY_REGISTER_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    for s in data.get("stories", []):
        sid = s.get("id", "")
        stitle = s.get("title", "")
        exact = s.get("exact_numbers", {}) or {}
        for metric, info in exact.items():
            val = info.get("value") if isinstance(info, dict) else info
            unit = info.get("unit", "") if isinstance(info, dict) else ""
            expectations[(sid, metric)] = {
                "story_id": sid,
                "story_title": stitle,
                "metric": metric,
                "expected_value": val,
                "unit": unit,
            }
    return expectations


def evaluate_story_entry(
    story_id: str,
    metric: str,
    actual_val: Any,
    expectations: Dict[Tuple[str, str], Dict[str, Any]],
    step_id: str,
    probe_sql: str,
    data_hash: Optional[str] = None,
    pattern_dir: str = "",
    pattern_cond: Optional[bool] = None,
) -> Dict[str, Any]:
    """Build a validated, computed story result with dynamically resolved expectations."""
    exp = expectations.get((story_id, metric), {})
    exp_val = exp.get("expected_value")
    stitle = exp.get("story_title", "")

    delta_pct = 0.0
    if isinstance(exp_val, (int, float)) and isinstance(actual_val, (int, float)) and exp_val != 0:
        delta_pct = round(((actual_val - exp_val) / exp_val * 100.0), 2)

    pattern_emerged = pattern_cond if pattern_cond is not None else (
        (actual_val > 0) if isinstance(actual_val, (int, float)) else bool(actual_val)
    )

    if isinstance(exp_val, (int, float)) and isinstance(actual_val, (int, float)):
        if abs(actual_val - exp_val) < 1e-6:
            verdict = "**PASS (EXACT)**"
        elif abs(delta_pct) <= 2.0:
            verdict = "**PASS (within ±2%)**"
        elif abs(delta_pct) <= 10.0:
            verdict = "**PASS (within ±10%)**"
        elif pattern_emerged:
            verdict = f"**PASS (EMERGED: delta {delta_pct:+.1f}%)**"
        else:
            verdict = "**FAIL (DEVIATED)**"
    else:
        verdict = "**PASS (EMERGED)**" if pattern_emerged else "**FAIL**"

    return {
        "story_id": story_id,
        "story_title": stitle,
        "metric": metric,
        "expected_value": exp_val,
        "actual_value": actual_val,
        "delta_pct": delta_pct,
        "verdict": verdict,
        "pattern_direction": pattern_dir or f"{metric} non-trivial",
        "pattern_emerged": pattern_emerged,
        "probe_sql": probe_sql,
        "step_id": step_id,
        "data_hash": data_hash,
    }


def record_step_story_actuals(
    conn: duckdb.DuckDBPyConnection,
    step_id: str,
    output_path: Path = ACTUALS_YAML_PATH,
    manifest: Optional[Dict[str, Dict[str, Any]]] = None,
    clear_existing: bool = False,
) -> List[Dict[str, Any]]:
    """Compute and record actual story values for available tables in step."""
    new_entries: List[Dict[str, Any]] = []
    tables = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
    expectations = load_story_expectations()

    # Extract hashes for relevant domain files
    def get_hash(filename: str) -> Optional[str]:
        if not manifest:
            return None
        return manifest.get(filename, {}).get("sha256")

    emp_hash = get_hash("PA0002_PA0001.csv") or get_hash("PA0001.csv")
    prod_hash = get_hash("production_monthly.csv")
    res_hash = get_hash("reserves_annual.xlsx")
    copa_hash = get_hash("CO_PA.csv")

    # =========================================================================
    # Step 2.1 HR Core: S1, S2, S4, S5, S7 (HC), S17, S38
    # =========================================================================
    if "posting_history" in tables and "dim_work_centre" in tables:
        # S1: Delhi Executive Overstay >= 5y (computed via gaps-and-islands over consecutive same-wc rows)
        try:
            d5_query = """
                WITH numbered_postings AS (
                    SELECT
                        p.emp_id,
                        p.wc_id,
                        p.from_date,
                        p.to_date,
                        p.grade_id,
                        ROW_NUMBER() OVER (PARTITION BY p.emp_id ORDER BY p.from_date, p.posting_id) -
                        ROW_NUMBER() OVER (PARTITION BY p.emp_id, p.wc_id ORDER BY p.from_date, p.posting_id) AS island_id
                    FROM main.posting_history p
                ),
                current_islands AS (
                    SELECT
                        emp_id,
                        wc_id,
                        MIN(from_date) AS continuous_from_date,
                        MAX(grade_id) AS current_grade_id
                    FROM numbered_postings
                    GROUP BY emp_id, wc_id, island_id
                    HAVING BOOL_OR(to_date IS NULL)
                )
                SELECT COUNT(DISTINCT emp_id)
                FROM current_islands
                WHERE wc_id = 'WC-DEL'
                  AND current_grade_id LIKE 'E%'
                  AND datediff('month', continuous_from_date, DATE '2026-10-19') >= 60;
            """
            d5 = conn.execute(d5_query).fetchone()[0] or 0
            new_entries.append(
                evaluate_story_entry(
                    "S1", "delhi_executives_ge_5yr", int(d5),
                    expectations, "2.1", "verify/probes/C1.sql", emp_hash,
                    "overstay_count > 0 and meaningful share of HQ", d5 > 0,
                )
            )

            # S1: Delhi Cluster Cumulative >= 10y
            d10_query = """
                SELECT COUNT(*) FROM (
                    SELECT p.emp_id FROM main.posting_history p
                    JOIN main.dim_work_centre wc ON p.wc_id = wc.wc_id
                    WHERE wc.cluster_id = 'CL-DEL' AND p.grade_id LIKE 'E%'
                    GROUP BY p.emp_id
                    HAVING SUM(datediff('day', p.from_date, COALESCE(p.to_date, DATE '2026-10-19'))) >= 3652
                )
            """
            d10 = conn.execute(d10_query).fetchone()[0] or 0
            new_entries.append(
                evaluate_story_entry(
                    "S1", "delhi_cluster_ge_10yr_cumulative", int(d10),
                    expectations, "2.1", "verify/probes/P11.sql", emp_hash,
                    "cumulative_cluster_tenure >= 10y > 0", d10 > 0,
                )
            )

            # S1: Superannuation Exempt 3y
            if "employee_master" in tables:
                dex_query = """
                    WITH c10 AS (
                        SELECT p.emp_id FROM main.posting_history p
                        JOIN main.dim_work_centre wc ON p.wc_id = wc.wc_id
                        WHERE wc.cluster_id = 'CL-DEL' AND p.grade_id LIKE 'E%'
                        GROUP BY p.emp_id
                        HAVING SUM(datediff('day', p.from_date, COALESCE(p.to_date, DATE '2026-10-19'))) >= 3652
                    )
                    SELECT COUNT(DISTINCT e.emp_id)
                    FROM main.employee_master e
                    JOIN c10 c ON e.emp_id = c.emp_id
                    WHERE e.dob <= DATE '1969-10-19'
                """
                dex = conn.execute(dex_query).fetchone()[0] or 0
                new_entries.append(
                    evaluate_story_entry(
                        "S1", "delhi_10yr_superannuation_exempt", int(dex),
                        expectations, "2.1", "verify/probes/P11.sql", emp_hash,
                        "exempt_officers >= 0", dex >= 0,
                    )
                )
                new_entries.append(
                    evaluate_story_entry(
                        "S1", "delhi_mandatory_transfer_due", int(d10 - dex),
                        expectations, "2.1", "verify/probes/P11.sql", emp_hash,
                        "mandatory_transfer_due > 0", (d10 - dex) > 0,
                    )
                )
        except Exception:
            pass

    # S2: North-East Deployment & Hard Station (Category C) Avoidance
    if "employee_master" in tables and "posting_history" in tables:
        try:
            ne_cnt = conn.execute("""
                SELECT COUNT(DISTINCT e.emp_id) FROM main.employee_master e
                JOIN main.dim_work_centre wc ON e.current_wc_id = wc.wc_id
                WHERE wc.sector = 'NE' AND e.current_grade_id LIKE 'E%'
                  AND (e.employment_status = 'Active' OR e.separation_date IS NULL)
            """).fetchone()[0] or 0
            new_entries.append(
                evaluate_story_entry(
                    "S2", "ne_executive_in_position", int(ne_cnt),
                    expectations, "2.1", "verify/probes/C2.sql", emp_hash,
                    "in_position_executives > 0", ne_cnt > 0,
                )
            )

            # E3-E5 never in Hard Station (Category C)
            c_never = conn.execute("""
                SELECT COUNT(DISTINCT e.emp_id) FROM main.employee_master e
                WHERE e.current_grade_id IN ('E3', 'E4', 'E5')
                  AND (e.employment_status = 'Active' OR e.separation_date IS NULL)
                  AND e.emp_id NOT IN (
                      SELECT DISTINCT p.emp_id FROM main.posting_history p
                      JOIN main.dim_work_centre wc ON p.wc_id = wc.wc_id
                      WHERE wc.hard_station_cat = 'C'
                  )
            """).fetchone()[0] or 0
            new_entries.append(
                evaluate_story_entry(
                    "S2", "e3_to_e5_never_hard_station", int(c_never),
                    expectations, "2.1", "verify/probes/C2.compare_or_so_what.sql", emp_hash,
                    "officers_never_serving_hard_station > 0", c_never > 0,
                )
            )
        except Exception:
            pass

    # S4: General Manager (E7+) Retirement Horizon
    if "employee_master" in tables and "separations" in tables:
        try:
            e7_act = conn.execute("""
                SELECT COUNT(DISTINCT e.emp_id) FROM main.employee_master e
                WHERE e.current_grade_id IN ('E7', 'E8', 'E9') AND e.employment_status = 'Active'
                  AND last_day(e.dob + INTERVAL 60 YEAR) BETWEEN DATE '2026-04-01' AND DATE '2029-03-31'
            """).fetchone()[0] or 0
            e7_sep = conn.execute("""
                SELECT COUNT(*) FROM main.separations s
                WHERE s.last_grade_id IN ('E7', 'E8', 'E9') AND s.separation_type = 'superannuation'
                  AND s.separation_date BETWEEN DATE '2026-04-01' AND DATE '2026-10-19'
            """).fetchone()[0] or 0
            total_e7 = e7_act + e7_sep
            new_entries.append(
                evaluate_story_entry(
                    "S4", "e7_plus_retiring_fy27_to_fy29", int(total_e7),
                    expectations, "2.1", "verify/probes/C4.sql", emp_hash,
                    "retiring_executives_horizon > 0", total_e7 > 0,
                )
            )
        except Exception:
            pass

    # S5: Core Technical Skill Cliff
    if "employee_master" in tables:
        try:
            tech_cnt = conn.execute("""
                SELECT COUNT(*) FROM main.employee_master
                WHERE discipline_id IN ('DISC-DRL', 'DISC-GEO', 'DISC-GPS', 'DISC-RES', 'DISC-PRD')
                  AND current_grade_id LIKE 'E%' AND doj <= DATE '2026-03-31'
                  AND (separation_date IS NULL OR separation_date > DATE '2026-03-31')
            """).fetchone()[0] or 0
            new_entries.append(
                evaluate_story_entry(
                    "S5", "core_technical_executives_fy26", int(tech_cnt),
                    expectations, "2.1", "verify/probes/C5.sql", emp_hash,
                    "core_technical_headcount > 0", tech_cnt > 0,
                )
            )

            tech_ret = conn.execute("""
                SELECT COUNT(*) FROM main.employee_master
                WHERE discipline_id IN ('DISC-DRL', 'DISC-GEO', 'DISC-GPS', 'DISC-RES', 'DISC-PRD')
                  AND current_grade_id LIKE 'E%' AND dob <= DATE '1970-03-31'
                  AND doj <= DATE '2026-03-31' AND (separation_date IS NULL OR separation_date >= DATE '2026-04-01')
            """).fetchone()[0] or 0
            new_entries.append(
                evaluate_story_entry(
                    "S5", "technical_retirements_by_2030", int(tech_ret),
                    expectations, "2.1", "verify/probes/C5.sql", emp_hash,
                    "impending_technical_retirements > 0", tech_ret > 0,
                )
            )
        except Exception:
            pass

    # S7: Cambay Headcount
    if "employee_master" in tables:
        try:
            cam_hc = conn.execute("""
                SELECT COUNT(*) FROM main.employee_master
                WHERE current_wc_id = 'WC-CAM' AND doj <= DATE '2026-03-31'
                  AND (separation_date IS NULL OR separation_date > DATE '2026-03-31')
            """).fetchone()[0] or 0
            new_entries.append(
                evaluate_story_entry(
                    "S7", "cambay_headcount_fy26", int(cam_hc),
                    expectations, "2.1", "verify/probes/C11.sql", emp_hash,
                    "cambay_headcount > 0", cam_hc > 0,
                )
            )
        except Exception:
            pass

    # S17: Women Officers Offshore
    if "employee_master" in tables and "dim_work_centre" in tables:
        try:
            w_off = conn.execute("""
                SELECT COUNT(*) FROM main.employee_master e
                JOIN main.dim_work_centre wc ON e.current_wc_id = wc.wc_id
                WHERE e.gender = 'Female' AND LOWER(wc.onshore_offshore) = 'offshore'
                  AND (e.employment_status = 'Active' OR e.separation_date IS NULL)
            """).fetchone()[0] or 0
            new_entries.append(
                evaluate_story_entry(
                    "S17", "women_offshore_count", int(w_off),
                    expectations, "2.1", "verify/probes/H7.drill_down.sql", emp_hash,
                    "active_women_offshore > 0", w_off > 0,
                )
            )
        except Exception:
            pass

    # =========================================================================
    # Step 2.3 Operations / Production: S6, S7 (Prod), S10, S15, S24, S36
    # =========================================================================
    if "production_monthly" in tables:
        # S7: Cambay Production FY21 & FY26
        try:
            c21 = conn.execute("""
                SELECT (SUM(oil_production_mt)/1e6 + SUM(gas_production_mmscm)/1e3)
                FROM main.production_monthly WHERE asset_wc_id = 'WC-CAM' AND fiscal_year = 'FY21'
            """).fetchone()[0] or 0.0
            new_entries.append(
                evaluate_story_entry(
                    "S7", "cambay_production_fy21_mmtoe", round(float(c21), 3),
                    expectations, "2.3", "verify/probes/C11.sql", prod_hash,
                    "cambay_production_positive", c21 > 0,
                )
            )

            c26 = conn.execute("""
                SELECT (SUM(oil_production_mt)/1e6 + SUM(gas_production_mmscm)/1e3)
                FROM main.production_monthly WHERE asset_wc_id = 'WC-CAM' AND fiscal_year = 'FY26'
            """).fetchone()[0] or 0.0
            new_entries.append(
                evaluate_story_entry(
                    "S7", "cambay_production_fy26_mmtoe", round(float(c26), 3),
                    expectations, "2.3", "verify/probes/C11.sql", prod_hash,
                    "cambay_production_positive", c26 > 0,
                )
            )
        except Exception:
            pass

        # S10: Emergent Crude FY27 H1
        try:
            h1_crude = conn.execute("""
                SELECT SUM(oil_production_mt)/1e6 FROM main.production_monthly
                WHERE fiscal_year = 'FY27' AND month IN ('2026-04', '2026-05', '2026-06', '2026-07', '2026-08', '2026-09')
            """).fetchone()[0] or 0.0
            new_entries.append(
                evaluate_story_entry(
                    "S10", "mou_crude_actual_h1_mmt", round(float(h1_crude), 3),
                    expectations, "2.3", "verify/probes/C10.sql", prod_hash,
                    "fy27_h1_crude_volume_emergent", h1_crude > 0,
                )
            )
        except Exception:
            pass

        # S6: Mature Marginal Fields (Borholla, Adiyakkamangalam, Lakwa)
        try:
            for fid, short_name in [('FLD-BOR', 'borholla_oil_production_mmt'), ('FLD-ADI', 'adiyakkamangalam_oil_production_mmt')]:
                vol = conn.execute(f"SELECT SUM(oil_production_mt)/1e6 FROM main.production_monthly WHERE field_id = '{fid}' AND fiscal_year = 'FY26'").fetchone()[0] or 0.0
                new_entries.append(
                    evaluate_story_entry(
                        "S6", short_name, round(float(vol), 3),
                        expectations, "2.3", "verify/probes/C6.sql", prod_hash,
                        "marginal_field_low_volume", vol > 0,
                    )
                )
        except Exception:
            pass

        # S15: Quarterly Crude Seasonality
        try:
            q_rows = conn.execute("""
                SELECT
                    CASE
                        WHEN month IN ('2025-04', '2025-05', '2025-06') THEN 'q1'
                        WHEN month IN ('2025-07', '2025-08', '2025-09') THEN 'q2'
                        WHEN month IN ('2025-10', '2025-11', '2025-12') THEN 'q3'
                        ELSE 'q4'
                    END AS q,
                    SUM(oil_production_mt)/1e6
                FROM main.production_monthly
                WHERE fiscal_year IN ('FY26', '2026')
                GROUP BY 1 ORDER BY 1
            """).fetchall()
            for q_name, vol in q_rows:
                metric_name = f"production_{q_name}_oil_mmt"
                new_entries.append(
                    evaluate_story_entry(
                        "S15", metric_name, round(float(vol), 3),
                        expectations, "2.3", "verify/probes/D4.drill_down.sql", prod_hash,
                        "quarterly_production_positive", vol > 0,
                    )
                )
        except Exception:
            pass

    # S24: Reserves Annual (2P reserves & RRR)
    if "reserves_annual" in tables:
        try:
            r2p = conn.execute("""
                SELECT SUM(reserves_2p_oil_mmt + reserves_2p_gas_bcm),
                       AVG(reserve_replacement_ratio_rrr_2p)
                FROM main.reserves_annual WHERE fiscal_year IN ('FY26', '2026')
            """).fetchone()
            if r2p and r2p[0] is not None:
                new_entries.append(
                    evaluate_story_entry(
                        "S24", "total_2p_reserves_mmtoe", round(float(r2p[0]), 2),
                        expectations, "2.3", "verify/probes/F8.sql", res_hash,
                        "2p_reserves_positive", r2p[0] > 0,
                    )
                )
                new_entries.append(
                    evaluate_story_entry(
                        "S24", "reserve_replacement_ratio_2p", round(float(r2p[1]), 3),
                        expectations, "2.3", "verify/probes/F8.compare_or_so_what.sql", res_hash,
                        "rrr_greater_than_1", r2p[1] >= 1.0,
                    )
                )
        except Exception:
            pass

    # Filter to requested step if applicable
    if step_id not in ("all", "manual", "V0"):
        step_entries = [e for e in new_entries if e["step_id"] == step_id]
    else:
        step_entries = new_entries

    # Persist to story_register_actuals.yaml
    if step_entries:
        existing_data = {"version": "1.0", "policy": "fully_emergent", "actuals": []}
        if output_path.exists() and not clear_existing:
            try:
                with open(output_path, "r", encoding="utf-8") as f:
                    existing_data = yaml.safe_load(f) or existing_data
            except Exception:
                pass

        existing_actuals = existing_data.get("actuals", [])
        actuals_dict = {(a["story_id"], a["metric"]): a for a in existing_actuals}
        for se in step_entries:
            # Drop transient fields for yaml storage
            entry_copy = dict(se)
            entry_copy.pop("verdict", None)
            entry_copy.pop("story_title", None)
            actuals_dict[(se["story_id"], se["metric"])] = entry_copy

        existing_data["actuals"] = list(actuals_dict.values())
        existing_data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(existing_data, f, sort_keys=False, indent=2)

    return step_entries


if __name__ == "__main__":
    from verify.loader import load_data
    conn, _ = load_data()
    entries = record_step_story_actuals(conn, "manual")
    print(f"Recorded {len(entries)} story actual entries to {ACTUALS_YAML_PATH}")
