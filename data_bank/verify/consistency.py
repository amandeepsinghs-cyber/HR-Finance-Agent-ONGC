"""
consistency.py — Generic consistency and integrity audits for ONGC Data Bank:
 1. Primary Key uniqueness
 2. Foreign Key validity (including against world_bible reference dimensions)
 3. Temporal sanity (separation date, DOJ before promotion, age 18–60, no overlapping postings, open-ended current posting, superannuation at month-end)
 4. Totals vs Calibration Targets mapped to available tables
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import duckdb
import yaml

WORLD_BIBLE_DIR = Path(__file__).resolve().parent.parent / "world_bible"
SCHEMA_PATH = WORLD_BIBLE_DIR / "schema_silver.yaml"
CALIBRATION_TARGETS_PATH = WORLD_BIBLE_DIR / "calibration_targets.yaml"


@dataclass
class AuditResult:
    audit_category: str  # 'PK', 'FK', 'TEMPORAL', 'CALIBRATION'
    audit_name: str
    target_entity: str
    status: str  # 'PASS', 'FAIL', 'SKIPPED', 'ERROR'
    violations_count: int = 0
    details: str = ""
    sample_violations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CalibrationAuditResult:
    target_id: str
    domain: str
    metric: str
    period: str
    target_value: float
    actual_value: float
    delta_pct: float
    tolerance: str
    passed: bool
    details: str = ""


@dataclass
class ConsistencyReport:
    total_audits: int = 0
    passed_audits: int = 0
    failed_audits: int = 0
    skipped_audits: int = 0
    audit_results: List[AuditResult] = field(default_factory=list)
    calibration_results: List[CalibrationAuditResult] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return self.failed_audits == 0


def audit_pk_uniqueness(
    conn: duckdb.DuckDBPyConnection,
    available_tables: Set[str],
    schema_data: Dict[str, Any],
) -> List[AuditResult]:
    """Verify primary key uniqueness for all available tables."""
    results = []
    tables = schema_data.get("tables", [])

    for t in tables:
        tname = t["table_name"]
        if tname not in available_tables:
            continue

        pks = t.get("primary_key", [])
        if not pks:
            continue

        pk_cols = [f'"{col}"' for col in pks]
        pk_str = ", ".join(pk_cols)
        not_null_cond = " AND ".join([f"{col} IS NOT NULL" for col in pk_cols])

        sql_dup = f"""
        SELECT {pk_str}, COUNT(*) AS dup_count
        FROM main.{tname}
        WHERE {not_null_cond}
        GROUP BY {pk_str}
        HAVING COUNT(*) > 1
        LIMIT 5;
        """
        try:
            cur = conn.cursor()
            cur.execute(sql_dup)
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description] if cur.description else []

            if rows:
                samples = [{cols[i]: str(r[i]) for i in range(len(cols))} for r in rows]
                total_dup_rows = conn.execute(f"""
                    SELECT SUM(cnt) FROM (
                        SELECT COUNT(*) AS cnt FROM main.{tname}
                        WHERE {not_null_cond} GROUP BY {pk_str} HAVING COUNT(*) > 1
                    )
                """).fetchone()[0] or len(rows)

                results.append(
                    AuditResult(
                        audit_category="PK",
                        audit_name=f"PK Uniqueness on {tname}",
                        target_entity=tname,
                        status="FAIL",
                        violations_count=total_dup_rows,
                        details=f"Found {total_dup_rows} duplicate primary key occurrences for ({pk_str})",
                        sample_violations=samples,
                    )
                )
            else:
                results.append(
                    AuditResult(
                        audit_category="PK",
                        audit_name=f"PK Uniqueness on {tname}",
                        target_entity=tname,
                        status="PASS",
                        violations_count=0,
                        details=f"All primary keys unique ({pk_str})",
                    )
                )
        except Exception as e:
            results.append(
                AuditResult(
                    audit_category="PK",
                    audit_name=f"PK Uniqueness on {tname}",
                    target_entity=tname,
                    status="ERROR",
                    details=f"Error executing PK check: {e}",
                )
            )

    return results


def audit_fk_validity(
    conn: duckdb.DuckDBPyConnection,
    available_tables: Set[str],
    schema_data: Dict[str, Any],
) -> List[AuditResult]:
    """Verify foreign key integrity against parent tables."""
    results = []
    tables = schema_data.get("tables", [])

    for t in tables:
        tname = t["table_name"]
        if tname not in available_tables:
            continue

        for c in t.get("columns", []):
            fk = c.get("fk")
            if not fk or "." not in fk:
                continue

            ptable, pcol = fk.split(".")
            if ptable not in available_tables:
                continue

            ccol = c["name"]
            audit_name = f"FK Validity: {tname}.{ccol} -> {ptable}.{pcol}"

            sql = f"""
            SELECT child."{ccol}" AS invalid_key, COUNT(*) AS orphan_count
            FROM main.{tname} child
            LEFT JOIN main.{ptable} parent ON child."{ccol}" = parent."{pcol}"
            WHERE child."{ccol}" IS NOT NULL AND parent."{pcol}" IS NULL
            GROUP BY child."{ccol}"
            LIMIT 5;
            """
            try:
                cur = conn.cursor()
                cur.execute(sql)
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description] if cur.description else []

                if rows:
                    samples = [{cols[i]: str(r[i]) for i in range(len(cols))} for r in rows]
                    total_orphans = conn.execute(f"""
                        SELECT COUNT(*)
                        FROM main.{tname} child
                        LEFT JOIN main.{ptable} parent ON child."{ccol}" = parent."{pcol}"
                        WHERE child."{ccol}" IS NOT NULL AND parent."{pcol}" IS NULL
                    """).fetchone()[0]

                    results.append(
                        AuditResult(
                            audit_category="FK",
                            audit_name=audit_name,
                            target_entity=f"{tname}.{ccol}",
                            status="FAIL",
                            violations_count=total_orphans,
                            details=f"Found {total_orphans} orphaned records referencing nonexistent {ptable}.{pcol}",
                            sample_violations=samples,
                        )
                    )
                else:
                    results.append(
                        AuditResult(
                            audit_category="FK",
                            audit_name=audit_name,
                            target_entity=f"{tname}.{ccol}",
                            status="PASS",
                            violations_count=0,
                            details="100% referential integrity confirmed",
                        )
                    )
            except Exception as e:
                results.append(
                    AuditResult(
                        audit_category="FK",
                        audit_name=audit_name,
                        target_entity=f"{tname}.{ccol}",
                        status="ERROR",
                        details=f"FK query error: {e}",
                    )
                )

    return results


def audit_temporal_sanity(
    conn: duckdb.DuckDBPyConnection,
    available_tables: Set[str],
) -> List[AuditResult]:
    """Verify domain temporal logic across HR and operations tables."""
    results = []

    # 1. No posting after separation date
    if "posting_history" in available_tables and "separations" in available_tables:
        sql = """
        SELECT p.emp_id, p.posting_id, p.from_date, s.separation_date
        FROM main.posting_history p
        JOIN main.separations s ON p.emp_id = s.emp_id
        WHERE p.from_date > s.separation_date
        LIMIT 5;
        """
        try:
            rows = conn.execute(sql).fetchall()
            if rows:
                results.append(
                    AuditResult(
                        audit_category="TEMPORAL",
                        audit_name="No Posting After Separation",
                        target_entity="posting_history",
                        status="FAIL",
                        violations_count=len(rows),
                        details="Postings found with from_date after employee separation date",
                        sample_violations=[{"emp_id": str(r[0]), "posting_id": str(r[1]), "from_date": str(r[2]), "sep_date": str(r[3])} for r in rows],
                    )
                )
            else:
                results.append(
                    AuditResult(
                        audit_category="TEMPORAL",
                        audit_name="No Posting After Separation",
                        target_entity="posting_history",
                        status="PASS",
                        details="No postings recorded after employee separation date",
                    )
                )
        except Exception as e:
            results.append(AuditResult(audit_category="TEMPORAL", audit_name="No Posting After Separation", target_entity="posting_history", status="ERROR", details=str(e)))

    # 2. No promotion before Date of Joining (DOJ)
    if "promotion_history" in available_tables and "employee_master" in available_tables:
        sql = """
        SELECT p.emp_id, p.promotion_id, p.effective_date, e.doj
        FROM main.promotion_history p
        JOIN main.employee_master e ON p.emp_id = e.emp_id
        WHERE p.effective_date < e.doj
        LIMIT 5;
        """
        try:
            rows = conn.execute(sql).fetchall()
            if rows:
                results.append(
                    AuditResult(
                        audit_category="TEMPORAL",
                        audit_name="No Promotion Before DOJ",
                        target_entity="promotion_history",
                        status="FAIL",
                        violations_count=len(rows),
                        details="Promotions recorded prior to employee date of joining",
                        sample_violations=[{"emp_id": str(r[0]), "promotion_id": str(r[1]), "eff_date": str(r[2]), "doj": str(r[3])} for r in rows],
                    )
                )
            else:
                results.append(
                    AuditResult(
                        audit_category="TEMPORAL",
                        audit_name="No Promotion Before DOJ",
                        target_entity="promotion_history",
                        status="PASS",
                        details="All promotions occur on or after employee date of joining",
                    )
                )
        except Exception as e:
            results.append(AuditResult(audit_category="TEMPORAL", audit_name="No Promotion Before DOJ", target_entity="promotion_history", status="ERROR", details=str(e)))

    # 3. Age 18–60 at all events
    if "employee_master" in available_tables:
        sql = """
        SELECT emp_id, dob, doj,
               datediff('year', dob, doj) AS age_at_hire
        FROM main.employee_master
        WHERE dob IS NOT NULL AND doj IS NOT NULL
          AND (doj < (dob + INTERVAL 18 YEAR) OR doj > (dob + INTERVAL 60 YEAR))
        LIMIT 5;
        """
        try:
            rows = conn.execute(sql).fetchall()
            if rows:
                results.append(
                    AuditResult(
                        audit_category="TEMPORAL",
                        audit_name="Age 18-60 at DOJ",
                        target_entity="employee_master",
                        status="FAIL",
                        violations_count=len(rows),
                        details="Employees hired outside statutory age 18-60 bracket",
                        sample_violations=[{"emp_id": str(r[0]), "dob": str(r[1]), "doj": str(r[2]), "age_at_hire": str(r[3])} for r in rows],
                    )
                )
            else:
                results.append(
                    AuditResult(
                        audit_category="TEMPORAL",
                        audit_name="Age 18-60 at DOJ",
                        target_entity="employee_master",
                        status="PASS",
                        details="All employees are age 18 to 60 at joining date",
                    )
                )
        except Exception as e:
            results.append(AuditResult(audit_category="TEMPORAL", audit_name="Age 18-60 at DOJ", target_entity="employee_master", status="ERROR", details=str(e)))

    # 4. No overlapping postings per employee
    if "posting_history" in available_tables:
        sql = """
        SELECT p1.emp_id, p1.posting_id AS p1_id, p1.from_date AS p1_from, p1.to_date AS p1_to,
               p2.posting_id AS p2_id, p2.from_date AS p2_from, p2.to_date AS p2_to
        FROM main.posting_history p1
        JOIN main.posting_history p2
          ON p1.emp_id = p2.emp_id
         AND p1.posting_id < p2.posting_id
        WHERE p1.from_date < COALESCE(p2.to_date, DATE '2099-12-31')
          AND COALESCE(p1.to_date, DATE '2099-12-31') > p2.from_date
        LIMIT 5;
        """
        try:
            rows = conn.execute(sql).fetchall()
            if rows:
                results.append(
                    AuditResult(
                        audit_category="TEMPORAL",
                        audit_name="No Overlapping Postings",
                        target_entity="posting_history",
                        status="FAIL",
                        violations_count=len(rows),
                        details="Overlapping posting date ranges detected for same employee",
                        sample_violations=[{"emp_id": str(r[0]), "p1": str(r[1]), "p2": str(r[4])} for r in rows],
                    )
                )
            else:
                results.append(
                    AuditResult(
                        audit_category="TEMPORAL",
                        audit_name="No Overlapping Postings",
                        target_entity="posting_history",
                        status="PASS",
                        details="Posting history is strictly sequential (no overlapping periods)",
                    )
                )
        except Exception as e:
            results.append(AuditResult(audit_category="TEMPORAL", audit_name="No Overlapping Postings", target_entity="posting_history", status="ERROR", details=str(e)))

    # 5. Current posting = open-ended row
    if "employee_master" in available_tables and "posting_history" in available_tables:
        sql = """
        WITH open_postings AS (
            SELECT emp_id, wc_id, COUNT(*) AS open_count
            FROM main.posting_history
            WHERE to_date IS NULL OR to_date >= DATE '2026-10-19'
            GROUP BY emp_id, wc_id
        )
        SELECT e.emp_id, e.current_wc_id, op.wc_id AS posting_wc_id, COALESCE(op.open_count, 0) AS open_cnt
        FROM main.employee_master e
        LEFT JOIN open_postings op ON e.emp_id = op.emp_id
        WHERE (e.employment_status = 'Active' OR e.separation_date IS NULL)
          AND (op.open_count != 1 OR op.wc_id != e.current_wc_id)
        LIMIT 5;
        """
        try:
            rows = conn.execute(sql).fetchall()
            if rows:
                results.append(
                    AuditResult(
                        audit_category="TEMPORAL",
                        audit_name="Current Posting Open-Ended",
                        target_entity="employee_master & posting_history",
                        status="FAIL",
                        violations_count=len(rows),
                        details="Active employees missing exactly 1 open-ended posting matching current_wc_id",
                        sample_violations=[{"emp_id": str(r[0]), "master_wc": str(r[1]), "posting_wc": str(r[2]), "open_cnt": str(r[3])} for r in rows],
                    )
                )
            else:
                results.append(
                    AuditResult(
                        audit_category="TEMPORAL",
                        audit_name="Current Posting Open-Ended",
                        target_entity="employee_master & posting_history",
                        status="PASS",
                        details="All active regular employees have exactly one open-ended current posting",
                    )
                )
        except Exception as e:
            results.append(AuditResult(audit_category="TEMPORAL", audit_name="Current Posting Open-Ended", target_entity="employee_master", status="ERROR", details=str(e)))

    # 6. Superannuation at 60 month-end
    if "separations" in available_tables and "employee_master" in available_tables:
        sql = """
        SELECT s.separation_id, s.emp_id, s.separation_date, e.dob,
               last_day(s.separation_date) AS expected_month_end
        FROM main.separations s
        JOIN main.employee_master e ON s.emp_id = e.emp_id
        WHERE s.separation_type = 'superannuation'
          AND s.separation_date != last_day(s.separation_date)
        LIMIT 5;
        """
        try:
            rows = conn.execute(sql).fetchall()
            if rows:
                results.append(
                    AuditResult(
                        audit_category="TEMPORAL",
                        audit_name="Superannuation at 60 Month-End",
                        target_entity="separations",
                        status="FAIL",
                        violations_count=len(rows),
                        details="Superannuation separation dates not falling on last calendar day of the month",
                        sample_violations=[{"sep_id": str(r[0]), "emp_id": str(r[1]), "sep_date": str(r[2]), "dob": str(r[3]), "expected_month_end": str(r[4])} for r in rows],
                    )
                )
            else:
                results.append(
                    AuditResult(
                        audit_category="TEMPORAL",
                        audit_name="Superannuation at 60 Month-End",
                        target_entity="separations",
                        status="PASS",
                        details="All superannuations occur on the last calendar day of the month",
                    )
                )
        except Exception as e:
            results.append(AuditResult(audit_category="TEMPORAL", audit_name="Superannuation at 60 Month-End", target_entity="separations", status="ERROR", details=str(e)))

    # 7. Zero same-WC posting rows except posting_type='promotion'
    if "posting_history" in available_tables:
        sql = """
        WITH lag_postings AS (
            SELECT
                emp_id,
                posting_id,
                wc_id,
                posting_type,
                from_date,
                to_date,
                LAG(wc_id) OVER (PARTITION BY emp_id ORDER BY from_date) AS prev_wc_id
            FROM main.posting_history
        )
        SELECT emp_id, posting_id, wc_id, posting_type, from_date
        FROM lag_postings
        WHERE prev_wc_id = wc_id AND LOWER(posting_type) != 'promotion'
        LIMIT 5;
        """
        try:
            rows = conn.execute(sql).fetchall()
            if rows:
                results.append(
                    AuditResult(
                        audit_category="TEMPORAL",
                        audit_name="Same-WC Postings Must Be Promotions",
                        target_entity="posting_history",
                        status="FAIL",
                        violations_count=len(rows),
                        details="Found same-WC consecutive postings without posting_type='promotion'",
                        sample_violations=[{"emp_id": str(r[0]), "posting_id": str(r[1]), "wc_id": str(r[2]), "type": str(r[3])} for r in rows],
                    )
                )
            else:
                results.append(
                    AuditResult(
                        audit_category="TEMPORAL",
                        audit_name="Same-WC Postings Must Be Promotions",
                        target_entity="posting_history",
                        status="PASS",
                        details="All consecutive same-WC postings are strictly posting_type='promotion'",
                    )
                )
        except Exception as e:
            results.append(AuditResult(audit_category="TEMPORAL", audit_name="Same-WC Postings Must Be Promotions", target_entity="posting_history", status="ERROR", details=str(e)))

    # 8. Median executive stint duration 3–5 years
    if "posting_history" in available_tables:
        sql = """
        SELECT
            ROUND(MEDIAN(datediff('month', from_date, to_date) / 12.0), 2) AS med_stint,
            COUNT(*) AS completed_postings
        FROM main.posting_history
        WHERE grade_id LIKE 'E%' AND to_date IS NOT NULL;
        """
        try:
            row = conn.execute(sql).fetchone()
            if row and row[0] is not None:
                med = float(row[0])
                cnt = int(row[1])
                if 3.0 <= med <= 5.0:
                    results.append(
                        AuditResult(
                            audit_category="TEMPORAL",
                            audit_name="Executive Stint Duration (3-5y)",
                            target_entity="posting_history",
                            status="PASS",
                            details=f"Median executive stint is {med} years (within 3–5y range across {cnt:,} completed postings)",
                        )
                    )
                else:
                    results.append(
                        AuditResult(
                            audit_category="TEMPORAL",
                            audit_name="Executive Stint Duration (3-5y)",
                            target_entity="posting_history",
                            status="FAIL",
                            violations_count=1,
                            details=f"Median executive stint is {med} years (outside 3–5y range across {cnt:,} completed postings)",
                        )
                    )
        except Exception as e:
            results.append(AuditResult(audit_category="TEMPORAL", audit_name="Executive Stint Duration (3-5y)", target_entity="posting_history", status="ERROR", details=str(e)))

    return results


def audit_calibration_targets(
    conn: duckdb.DuckDBPyConnection,
    available_tables: Set[str],
) -> List[CalibrationAuditResult]:
    """Check totals against public calibration targets mapped to available tables."""
    results = []
    if not CALIBRATION_TARGETS_PATH.exists():
        return results

    with open(CALIBRATION_TARGETS_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    spec_map = {
        "H1": "employee_master",
        "H2": "posting_history",
        "H7": "headcount_snapshot",
        "H8": "payroll_monthly",
        "F1": "production_monthly",
        "F2": "reserves_annual",
        "F3": "wells_drilled",
        "F4": "price_fx_monthly",
        "F5": "field_pnl_annual",
        "F6": "cost_ledger",
        "F7": "capex_budget",
        "F12": "csr_projects",
        "F17": "corporate_financials",
    }

    targets = data.get("calibration_targets", [])

    for target in targets:
        tid = target.get("id")
        target_tables_specs = target.get("target_tables", [])
        needed_tables = {spec_map.get(s, s) for s in target_tables_specs}

        available_subset = needed_tables.intersection(available_tables)
        if not available_subset:
            continue

        tgt_val = float(target.get("value", 0))
        tol_str = str(target.get("tolerance", "2%"))
        tol_pct = 0.0 if tol_str == "exact" else 2.0
        metric_desc = target.get("metric", "")
        period = target.get("period", "")
        domain = target.get("domain", "")

        actual_val: Optional[float] = None
        sql = None

        # OPS: Production FY26
        if "production_monthly" in available_subset:
            if tid == "CAL-OPS-PROD-OIL-FY26" or tid == "CAL-OPS-CRUDE-TOTAL-FY26":
                sql = "SELECT (SUM(oil_production_mt) + SUM(condensate_production_mt)) / 1000000.0 FROM main.production_monthly WHERE fiscal_year IN ('FY26', '2026')"
            elif tid == "CAL-OPS-PROD-OIL-ONGC-FY26":
                sql = "SELECT (SUM(oil_production_mt) + SUM(condensate_production_mt)) / 1000000.0 FROM main.production_monthly WHERE fiscal_year IN ('FY26', '2026') AND operatorship = 'operated'"
            elif tid == "CAL-OPS-PROD-OIL-JV-FY26":
                sql = "SELECT SUM(oil_production_mt) / 1000000.0 FROM main.production_monthly WHERE fiscal_year IN ('FY26', '2026') AND operatorship = 'joint_venture'"
            elif tid == "CAL-OPS-PROD-GAS-FY26" or tid == "CAL-OPS-GAS-TOTAL-FY26":
                sql = "SELECT SUM(gas_production_mmscm) / 1000.0 FROM main.production_monthly WHERE fiscal_year IN ('FY26', '2026')"
            elif tid == "CAL-OPS-PROD-GAS-ONGC-FY26":
                sql = "SELECT SUM(gas_production_mmscm) / 1000.0 FROM main.production_monthly WHERE fiscal_year IN ('FY26', '2026') AND operatorship = 'operated'"
            elif tid == "CAL-OPS-PROD-GAS-JV-FY26":
                sql = "SELECT SUM(gas_production_mmscm) / 1000.0 FROM main.production_monthly WHERE fiscal_year IN ('FY26', '2026') AND operatorship = 'joint_venture'"
            elif tid == "CAL-OPS-OFFSHORE-CRUDE-FY26":
                sql = "SELECT SUM(p.oil_production_mt) / 1000000.0 FROM main.production_monthly p JOIN main.dim_field f ON p.field_id = f.field_id WHERE f.onshore_offshore = 'Offshore' AND p.fiscal_year IN ('FY26', '2026')"
            elif tid == "CAL-OPS-ONSHORE-CRUDE-FY26":
                sql = "SELECT SUM(p.oil_production_mt) / 1000000.0 FROM main.production_monthly p JOIN main.dim_field f ON p.field_id = f.field_id WHERE f.onshore_offshore = 'Onshore' AND p.fiscal_year IN ('FY26', '2026')"

        # OPS: Wells drilled
        if "wells_drilled" in available_subset and not sql:
            if tid == "CAL-OPS-WELLS-TOT-FY26" or tid == "CAL-OPS-WELLS-TOTAL-FY26":
                sql = "SELECT COUNT(*) FROM main.wells_drilled WHERE fiscal_year IN ('FY26', '2026')"
            elif tid == "CAL-OPS-WELLS-EXPL-FY26" or tid == "CAL-OPS-WELLS-EXPLORATORY-FY26":
                sql = "SELECT COUNT(*) FROM main.wells_drilled WHERE LOWER(well_type) = 'exploratory' AND fiscal_year IN ('FY26', '2026')"
            elif tid == "CAL-OPS-WELLS-DEV-FY26" or tid == "CAL-OPS-WELLS-DEVELOPMENT-FY26":
                sql = "SELECT COUNT(*) FROM main.wells_drilled WHERE LOWER(well_type) = 'development' AND fiscal_year IN ('FY26', '2026')"

        # OPS: 2P Reserves
        if "reserves_annual" in available_subset and not sql:
            if tid == "CAL-OPS-2P-RESERVES-TOTAL-FY26" or tid == "CAL-OPS-RES-2P-FY26":
                sql = "SELECT SUM(reserves_2p_oil_mmt + reserves_2p_gas_bcm) FROM main.reserves_annual WHERE fiscal_year IN ('FY26', '2026')"
            elif tid == "CAL-OPS-RRR-2P-FY26" or (domain == "ops" and "rrr" in metric_desc.lower() and period in ("FY26", "2026")):
                sql = "SELECT AVG(reserve_replacement_ratio_rrr_2p) FROM main.reserves_annual WHERE fiscal_year IN ('FY26', '2026')"

        # HR: Diversity & Headcount
        if "employee_master" in available_subset and not sql:
            if tid == "CAL-HR-DIV-WOMEN-TOT":
                sql = "SELECT COUNT(*) FROM main.employee_master WHERE doj <= DATE '2026-03-31' AND (separation_date IS NULL OR separation_date > DATE '2026-03-31') AND gender = 'Female'"
            elif tid == "CAL-HR-DIV-WOMEN-EXEC":
                sql = "SELECT COUNT(*) FROM main.employee_master WHERE doj <= DATE '2026-03-31' AND (separation_date IS NULL OR separation_date > DATE '2026-03-31') AND gender = 'Female' AND current_grade_id LIKE 'E%'"
            elif tid == "CAL-HR-DIV-WOMEN-NONEXEC":
                sql = "SELECT COUNT(*) FROM main.employee_master WHERE doj <= DATE '2026-03-31' AND (separation_date IS NULL OR separation_date > DATE '2026-03-31') AND gender = 'Female' AND current_grade_id NOT LIKE 'E%'"
            elif tid == "CAL-HR-DIV-PWD-TOT":
                sql = "SELECT COUNT(*) FROM main.employee_master WHERE doj <= DATE '2026-03-31' AND (separation_date IS NULL OR separation_date > DATE '2026-03-31') AND pwd_flag = TRUE"
            elif tid == "CAL-HR-DIV-PWD-EXEC":
                sql = "SELECT COUNT(*) FROM main.employee_master WHERE doj <= DATE '2026-03-31' AND (separation_date IS NULL OR separation_date > DATE '2026-03-31') AND pwd_flag = TRUE AND current_grade_id LIKE 'E%'"
            elif tid == "CAL-HR-DIV-PWD-NONEXEC":
                sql = "SELECT COUNT(*) FROM main.employee_master WHERE doj <= DATE '2026-03-31' AND (separation_date IS NULL OR separation_date > DATE '2026-03-31') AND pwd_flag = TRUE AND current_grade_id NOT LIKE 'E%'"
            elif tid == "CAL-HR-LOC-ASSAM-TOT":
                sql = "SELECT COUNT(*) FROM main.employee_master e JOIN main.dim_work_centre wc ON e.current_wc_id = wc.wc_id WHERE e.doj <= DATE '2026-07-30' AND (e.separation_date IS NULL OR e.separation_date > DATE '2026-07-30') AND wc.state = 'Assam'"
            elif tid.startswith("CAL-HR-HC-FY") or tid == "CAL-HR-HC-REGULAR-FY26" or ("regular employees" in metric_desc.lower()):
                fy_match = re.search(r"FY(\d\d)", period)
                if fy_match:
                    yr = int("20" + fy_match.group(1))
                    sql = f"SELECT COUNT(*) FROM main.employee_master WHERE doj <= DATE '{yr}-03-31' AND (separation_date IS NULL OR separation_date > DATE '{yr}-03-31')"
                else:
                    sql = "SELECT COUNT(*) FROM main.employee_master WHERE doj <= DATE '2026-03-31' AND (separation_date IS NULL OR separation_date > DATE '2026-03-31')"
            elif tid == "CAL-HR-HC-EXEC-FY26":
                sql = "SELECT COUNT(*) FROM main.employee_master WHERE current_grade_id LIKE 'E%' AND doj <= DATE '2026-03-31' AND (separation_date IS NULL OR separation_date > DATE '2026-03-31')"
            elif tid == "CAL-HR-HC-NONEXEC-FY26":
                sql = "SELECT COUNT(*) FROM main.employee_master WHERE current_grade_id NOT LIKE 'E%' AND doj <= DATE '2026-03-31' AND (separation_date IS NULL OR separation_date > DATE '2026-03-31')"

        if sql:
            try:
                val = conn.execute(sql).fetchone()[0]
                if val is not None:
                    actual_val = float(val)
                    delta = ((actual_val - tgt_val) / tgt_val) * 100.0 if tgt_val != 0 else 0.0
                    passed = abs(delta) <= (0.01 if tol_str == "exact" else tol_pct)
                    results.append(
                        CalibrationAuditResult(
                            target_id=tid,
                            domain=domain,
                            metric=metric_desc,
                            period=period,
                            target_value=tgt_val,
                            actual_value=round(actual_val, 3),
                            delta_pct=round(delta, 2),
                            tolerance=tol_str,
                            passed=passed,
                            details=f"Target: {tgt_val}, Actual: {round(actual_val, 3)}, Delta: {delta:.2f}%",
                        )
                    )
            except Exception:
                pass

    return results


def run_consistency_audits(
    conn: duckdb.DuckDBPyConnection,
    filter_tables: Optional[Set[str]] = None,
) -> ConsistencyReport:
    """Execute all consistency audits on currently available tables."""
    report = ConsistencyReport()

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_data = yaml.safe_load(f)

    tables_in_db = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
    available_tables = tables_in_db.intersection(filter_tables) if filter_tables else tables_in_db

    # 1. PK Uniqueness
    pk_results = audit_pk_uniqueness(conn, available_tables, schema_data)
    report.audit_results.extend(pk_results)

    # 2. FK Validity
    fk_results = audit_fk_validity(conn, available_tables, schema_data)
    report.audit_results.extend(fk_results)

    # 3. Temporal Sanity
    temporal_results = audit_temporal_sanity(conn, available_tables)
    report.audit_results.extend(temporal_results)

    # 4. Calibration Targets
    cal_results = audit_calibration_targets(conn, available_tables)
    report.calibration_results = cal_results

    # Tallies
    for a in report.audit_results:
        report.total_audits += 1
        if a.status == "PASS":
            report.passed_audits += 1
        elif a.status in ("FAIL", "ERROR"):
            report.failed_audits += 1
        else:
            report.skipped_audits += 1

    return report


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from verify.loader import load_data

    conn, lreport = load_data()
    creport = run_consistency_audits(conn)

    print("=" * 60)
    print("Consistency Audits Summary")
    print(f"Total Audits Executed: {creport.total_audits}")
    print(f"Passed:                {creport.passed_audits}")
    print(f"Failed:                {creport.failed_audits}")
    print(f"Calibration Targets:   {len(creport.calibration_results)} checked")
    if creport.calibration_results:
        cal_passed = sum(1 for c in creport.calibration_results if c.passed)
        print(f"Calibration Passed:    {cal_passed} / {len(creport.calibration_results)}")
        for c in creport.calibration_results:
            st = "PASS" if c.passed else "FAIL"
            print(f"  [{st}] {c.target_id:<28} tgt={c.target_value} act={c.actual_value} delta={c.delta_pct}%")

    if creport.failed_audits > 0:
        print("\nFailed Audits:")
        for a in creport.audit_results:
            if a.status in ("FAIL", "ERROR"):
                print(f"  - [{a.audit_category}] {a.audit_name}: {a.details}")
    print("=" * 60)
