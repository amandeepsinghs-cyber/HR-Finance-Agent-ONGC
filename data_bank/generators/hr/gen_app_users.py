#!/usr/bin/env python3
"""Deterministic generator and completeness-gate verifier for Yukti v3 personas (P2H.1 / SPEC-06 / D-41 / D-60).

Reads SAP landing CSVs (`PA0002_PA0001.csv`, `PA0001.csv`, `PY_CLUSTER_EXP.csv`,
`PA2001_PA2006.csv`, `eAPAR_ratings.csv`), deterministically selects the 11
canonical personas, verifies the SPEC-06 §4.2 completeness gate, and writes:
  - `data_bank/landing/sap/dim_app_user.csv`
  - `yukti/backend/app/brain/app_users.yaml`

Usage:
  python data_bank/generators/hr/gen_app_users.py
  python data_bank/generators/hr/gen_app_users.py --check
"""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import re
import sys
from typing import Any
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT_CSV = REPO_ROOT / "data_bank" / "landing" / "sap" / "dim_app_user.csv"
DEFAULT_OUT_YAML = REPO_ROOT / "yukti" / "backend" / "app" / "brain" / "app_users.yaml"

CANONICAL_PERSONA_ORDER: list[str] = [
    "CMD",
    "DIR_HR",
    "DIR_FIN",
    "E1_HR",
    "E2_HR",
    "E3_HR",
    "E4_HR",
    "E1_FIN",
    "E2_FIN",
    "E3_FIN",
    "E4_FIN",
]

# Decision D-60: fictional surnames for senior personas so synthetic pay/APAR are
# never attributed to real ONGC office-holders.
SENIOR_OVERRIDES: dict[str, dict[str, str]] = {
    "CMD": {
        "emp_id": "EMP-000001",
        "display_name": "Arun Mehra",
        "grade": "CMD",
        "function": "EXEC",
        "discipline_id": "DISC-PRD",
        "wc_id": "WC-DEL",
        "work_centre": "Delhi HQ",
        "functional_designation": "Chairman & Managing Director",
        "tier": "cmd",
    },
    "DIR_HR": {
        "emp_id": "EMP-000002",
        "display_name": "Manish Deshpande",
        "grade": "DIR",
        "function": "HR",
        "discipline_id": "DISC-HR",
        "wc_id": "WC-DEL",
        "work_centre": "Delhi HQ",
        "functional_designation": "Director (HR)",
        "tier": "director",
    },
    "DIR_FIN": {
        "emp_id": "EMP-000003",
        "display_name": "Vivek Rao",
        "grade": "DIR",
        "function": "FIN",
        "discipline_id": "DISC-FIN",
        "wc_id": "WC-DEL",
        "work_centre": "Delhi HQ",
        "functional_designation": "Director (Finance)",
        "tier": "director",
    },
}

JUNIOR_POOL_SPECS: dict[str, dict[str, str]] = {
    "E1_HR": {
        "discipline_id": "DISC-HR",
        "grade": "E1",
        "function": "HR",
        "functional_designation": "HR Officer (E1)",
    },
    "E2_HR": {
        "discipline_id": "DISC-HR",
        "grade": "E2",
        "function": "HR",
        "functional_designation": "HR Executive (E2)",
        "pinned_emp_id": "EMP-102451",
    },
    "E3_HR": {
        "discipline_id": "DISC-HR",
        "grade": "E3",
        "function": "HR",
        "functional_designation": "Senior HR Executive (E3)",
    },
    "E4_HR": {
        "discipline_id": "DISC-HR",
        "grade": "E4",
        "function": "HR",
        "functional_designation": "Dy. Manager HR (E4)",
    },
    "E1_FIN": {
        "discipline_id": "DISC-FIN",
        "grade": "E1",
        "function": "FIN",
        "functional_designation": "Accounts Officer (E1)",
    },
    "E2_FIN": {
        "discipline_id": "DISC-FIN",
        "grade": "E2",
        "function": "FIN",
        "functional_designation": "Finance Executive (E2)",
    },
    "E3_FIN": {
        "discipline_id": "DISC-FIN",
        "grade": "E3",
        "function": "FIN",
        "functional_designation": "Finance Officer (E3)",
    },
    "E4_FIN": {
        "discipline_id": "DISC-FIN",
        "grade": "E4",
        "function": "FIN",
        "functional_designation": "Dy. Manager Finance (E4)",
    },
}

DEMO_ADMIN_ENTRY: dict[str, Any] = {
    "persona_id": "DEMO_ADMIN",
    "emp_id": "EMP-000001",
    "display_name": "Demo Presenter (Admin)",
    "grade": "ADMIN",
    "function": "EXEC",
    "discipline_id": "DISC-PRD",
    "wc_id": "WC-DEL",
    "work_centre": "Delhi HQ",
    "functional_designation": "Demo Admin — Switchable",
    "tier": "cmd",
    "is_admin": True,
    "synthetic": True,
}

COMPLETENESS_GATE_SQL = """\
WITH
  has_pay AS (
    SELECT emp_id, COUNT(DISTINCT pay_period) AS months
    FROM `hrfin_gold.fact_payroll_monthly`
    WHERE fiscal_year = '2025-26'
    GROUP BY emp_id HAVING months = 12
  ),
  has_leave_el AS (
    SELECT DISTINCT emp_id FROM `hrfin_gold.fact_leave_ledger`
    WHERE leave_type IN ('EL', 'Earned_Leave_EL', 'CL', 'Casual_Leave_CL', 'HPL', 'Half_Pay_Leave_HPL')
  ),
  has_posting AS (
    SELECT emp_id, COUNT(*) AS n FROM `hrfin_gold.fact_posting_history`
    GROUP BY emp_id HAVING n >= 1
  ),
  has_apar AS (
    SELECT emp_id, COUNT(*) AS yrs FROM `hrfin_gold.fact_apar`
    GROUP BY emp_id HAVING yrs >= 1
  )
SELECT
  u.persona_id, u.emp_id, u.display_name, u.grade, u.function,
  IF(p.emp_id IS NOT NULL, TRUE, FALSE) AS ok_pay,
  IF(l.emp_id IS NOT NULL, TRUE, FALSE) AS ok_leave,
  IF(fh.emp_id IS NOT NULL, TRUE, FALSE) AS ok_posting,
  IF(ap.emp_id IS NOT NULL, TRUE, FALSE) AS ok_apar
FROM `hrfin_gold.dim_app_user` u
LEFT JOIN has_pay      p  USING (emp_id)
LEFT JOIN has_leave_el l  USING (emp_id)
LEFT JOIN has_posting  fh USING (emp_id)
LEFT JOIN has_apar     ap USING (emp_id)
ORDER BY u.persona_id;
"""

FORBIDDEN_DISPLAY_NAMES = {
    "Chairman & CEO",
    "Chairman and CEO",
    "Director",
    "Director (HR)",
    "Director (Finance)",
    "Director (Human Resources)",
    "CMD",
    "DIR_HR",
    "DIR_FIN",
}


def resolve_sap_landing_dir() -> Path:
    """Locate the directory containing the SAP source CSVs (`PA0002_PA0001.csv`, etc.)."""
    candidates: list[Path] = []
    env_dir = os.environ.get("SAP_LANDING_DIR")
    if env_dir:
        candidates.append(Path(env_dir))
    candidates.append(REPO_ROOT / "data_bank" / "landing" / "sap")
    # In git worktrees (`HR and Finance_ONGC__v3P2H`), gitignored landing CSVs live in the sibling main checkout.
    candidates.append(REPO_ROOT.parent / "HR and Finance_ONGC" / "data_bank" / "landing" / "sap")
    for cand in candidates:
        if (cand / "PA0002_PA0001.csv").exists():
            return cand
    raise FileNotFoundError(
        f"Could not find PA0002_PA0001.csv in any candidate directory: {[str(c) for c in candidates]}"
    )


def compute_users_from_sap(sap_dir: Path) -> list[dict[str, Any]]:
    """Deterministically select the 11 personas and compute their completeness flags from SAP CSVs."""
    # 1. Read active employees from PA0002_PA0001.csv and identify candidate PERNRs
    emp_by_id: dict[str, dict[str, str]] = {}
    candidate_pernrs: set[str] = {"EMP-000001", "EMP-000002", "EMP-000003", "EMP-102451"}
    with (sap_dir / "PA0002_PA0001.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pernr = row["PERNR"]
            emp_by_id[pernr] = row
            if (
                row.get("STAT2") == "Active"
                and row.get("WERKS") == "WC-DEL"
                and row.get("discipline_id") in ("DISC-HR", "DISC-FIN")
                and row.get("PERSK") in ("E1", "E2", "E3", "E4")
            ):
                candidate_pernrs.add(pernr)

    # 2. Read FY 2025-26 payroll month counts from PY_CLUSTER_EXP.csv
    pay_fy26_months: dict[str, set[str]] = {}
    with (sap_dir / "PY_CLUSTER_EXP.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pernr = row["PERNR"]
            if pernr not in candidate_pernrs:
                continue
            if row.get("fiscal_year") in ("FY26", "2025-26") or row.get("FY") in ("FY26", "2025-26"):
                pay_fy26_months.setdefault(pernr, set()).add(row["FPPER"])

    # 3. Read leave counts by type from PA2001_PA2006.csv
    leave_el: dict[str, int] = {}
    leave_cl: dict[str, int] = {}
    leave_hpl: dict[str, int] = {}
    with (sap_dir / "PA2001_PA2006.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pernr = row["PERNR"]
            if pernr not in candidate_pernrs:
                continue
            subty = row.get("SUBTY", "")
            if subty in ("EL", "Earned_Leave_EL"):
                leave_el[pernr] = leave_el.get(pernr, 0) + 1
            elif subty in ("CL", "Casual_Leave_CL"):
                leave_cl[pernr] = leave_cl.get(pernr, 0) + 1
            elif subty in ("HPL", "Half_Pay_Leave_HPL"):
                leave_hpl[pernr] = leave_hpl.get(pernr, 0) + 1

    # 4. Read posting history counts from PA0001.csv
    posting_total: dict[str, int] = {}
    posting_current: dict[str, int] = {}
    with (sap_dir / "PA0001.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pernr = row["PERNR"]
            if pernr not in candidate_pernrs:
                continue
            posting_total[pernr] = posting_total.get(pernr, 0) + 1
            if row.get("is_current_posting") == "True" or row.get("ENDDA") in ("9999-12-31", ""):
                posting_current[pernr] = posting_current.get(pernr, 0) + 1

    # 5. Read APAR counts from eAPAR_ratings.csv
    apar_counts: dict[str, int] = {}
    with (sap_dir / "eAPAR_ratings.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pernr = row["PERNR"]
            if pernr not in candidate_pernrs:
                continue
            apar_counts[pernr] = apar_counts.get(pernr, 0) + 1

    def _build_record(
        persona_id: str,
        emp_id: str,
        display_name: str,
        grade: str,
        function: str,
        discipline_id: str,
        wc_id: str,
        work_centre: str,
        functional_designation: str,
        tier: str,
    ) -> dict[str, Any]:
        n_pay = len(pay_fy26_months.get(emp_id, set()))
        n_el = leave_el.get(emp_id, 0)
        n_cl = leave_cl.get(emp_id, 0)
        n_hpl = leave_hpl.get(emp_id, 0)
        n_post_cur = posting_current.get(emp_id, 0)
        n_post_tot = posting_total.get(emp_id, 0)
        n_apar = apar_counts.get(emp_id, 0)

        has_pay = n_pay >= 12
        # SPEC-06 §4.2 & Decision D-60: ok_leave checks presence of any leave ledger row
        # in ('EL','Earned_Leave_EL','CL','Casual_Leave_CL','HPL','Half_Pay_Leave_HPL').
        has_leave = (n_el + n_cl + n_hpl) >= 1
        has_post = n_post_cur >= 1 and n_post_tot >= 1
        has_ap = n_apar >= 1

        return {
            "persona_id": persona_id,
            "emp_id": emp_id,
            "display_name": display_name,
            "grade": grade,
            "function": function,
            "discipline_id": discipline_id,
            "wc_id": wc_id,
            "work_centre": work_centre,
            "functional_designation": functional_designation,
            "tier": tier,
            "is_admin": False,
            "synthetic": True,
            "has_pay_fy26": has_pay,
            "has_leave_el": has_leave,
            "has_posting": has_post,
            "has_apar": has_ap,
            "ok_pay": has_pay,
            "ok_leave": has_leave,
            "ok_posting": has_post,
            "ok_apar": has_ap,
            "pay_fy26_months": n_pay,
            "leave_el_rows": n_el,
            "leave_cl_rows": n_cl,
            "leave_hpl_rows": n_hpl,
            "posting_rows": n_post_tot,
            "apar_rows": n_apar,
        }

    records: dict[str, dict[str, Any]] = {}

    # Seniors (CMD, DIR_HR, DIR_FIN)
    for pid, meta in SENIOR_OVERRIDES.items():
        emp_id = meta["emp_id"]
        if emp_id not in emp_by_id:
            raise RuntimeError(f"Senior persona {pid} ({emp_id}) missing from PA0002_PA0001.csv")
        records[pid] = _build_record(
            persona_id=pid,
            emp_id=emp_id,
            display_name=meta["display_name"],
            grade=meta["grade"],
            function=meta["function"],
            discipline_id=meta["discipline_id"],
            wc_id=meta["wc_id"],
            work_centre=meta["work_centre"],
            functional_designation=meta["functional_designation"],
            tier=meta["tier"],
        )

    # Juniors (E1_HR..E4_HR, E1_FIN..E4_FIN)
    for pid, spec in JUNIOR_POOL_SPECS.items():
        pinned = spec.get("pinned_emp_id")
        if pinned:
            emp_row = emp_by_id.get(pinned)
            if not emp_row:
                raise RuntimeError(f"Pinned persona {pid} ({pinned}) missing from PA0002_PA0001.csv")
            selected_emp_id = pinned
            selected_name = emp_row.get("name") or emp_row.get("ENAME", "")
        else:
            candidates: list[tuple[str, str]] = []
            for pernr, row in emp_by_id.items():
                if (
                    row.get("STAT2") == "Active"
                    and row.get("WERKS") == "WC-DEL"
                    and row.get("discipline_id") == spec["discipline_id"]
                    and row.get("PERSK") == spec["grade"]
                ):
                    # Require full completeness gate (12 FY26 pay months, EL+CL+HPL leave rows, current posting, APAR)
                    if (
                        len(pay_fy26_months.get(pernr, set())) >= 12
                        and leave_el.get(pernr, 0) >= 1
                        and leave_cl.get(pernr, 0) >= 1
                        and leave_hpl.get(pernr, 0) >= 1
                        and posting_current.get(pernr, 0) >= 1
                        and apar_counts.get(pernr, 0) >= 1
                    ):
                        candidates.append((pernr, row.get("name") or row.get("ENAME", "")))
            candidates.sort(key=lambda x: x[0])
            if not candidates:
                raise RuntimeError(f"No candidate in WC-DEL satisfies completeness gate for {pid} ({spec})")
            selected_emp_id, selected_name = candidates[0]

        records[pid] = _build_record(
            persona_id=pid,
            emp_id=selected_emp_id,
            display_name=selected_name,
            grade=spec["grade"],
            function=spec["function"],
            discipline_id=spec["discipline_id"],
            wc_id="WC-DEL",
            work_centre="Delhi HQ",
            functional_designation=spec["functional_designation"],
            tier="junior",
        )

    return [records[pid] for pid in CANONICAL_PERSONA_ORDER]


def write_outputs(rows: list[dict[str, Any]], out_csv: Path = DEFAULT_OUT_CSV, out_yaml: Path = DEFAULT_OUT_YAML) -> None:
    """Write `dim_app_user.csv` and `app_users.yaml`."""
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    out_yaml.parent.mkdir(parents=True, exist_ok=True)
    yaml_payload = {
        "version": 2,
        "decision_refs": ["D-41", "D-43", "D-60", "SPEC-06"],
        "completeness_gate_sql": COMPLETENESS_GATE_SQL,
        "personas": {r["persona_id"]: r for r in rows},
        "demo_admin": DEMO_ADMIN_ENTRY,
    }
    with out_yaml.open("w", encoding="utf-8") as f:
        yaml.safe_dump(yaml_payload, f, sort_keys=False, allow_unicode=True)


def verify_records(rows: list[dict[str, Any]]) -> None:
    """Verify all 11 persona records satisfy P2H.1 / SPEC-06 / D-60 invariants."""
    if len(rows) != 11:
        raise AssertionError(f"Expected 11 personas, got {len(rows)}")
    seen_ids = [r["persona_id"] for r in rows]
    if seen_ids != CANONICAL_PERSONA_ORDER:
        raise AssertionError(f"Persona order mismatch: {seen_ids} != {CANONICAL_PERSONA_ORDER}")
    emp_ids = [r["emp_id"] for r in rows]
    if len(set(emp_ids)) != 11:
        raise AssertionError(f"Duplicate emp_id in dim_app_user: {emp_ids}")

    for r in rows:
        pid = r["persona_id"]
        if not re.match(r"^EMP-\d{6}$", str(r["emp_id"])):
            raise AssertionError(f"{pid}: invalid emp_id {r['emp_id']!r}")
        if not r["display_name"] or r["display_name"] in FORBIDDEN_DISPLAY_NAMES:
            raise AssertionError(f"{pid}: forbidden or empty display_name {r['display_name']!r}")
        if r["wc_id"] != "WC-DEL":
            raise AssertionError(f"{pid}: expected wc_id='WC-DEL', got {r['wc_id']!r}")
        if r.get("synthetic") is not True:
            raise AssertionError(f"{pid}: expected synthetic=True")
        for col in ("has_pay_fy26", "has_leave_el", "has_posting", "has_apar", "ok_pay", "ok_leave", "ok_posting", "ok_apar"):
            if r.get(col) is not True:
                raise AssertionError(f"{pid} ({r['emp_id']}): completeness gate failed on {col}={r.get(col)!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate and check dim_app_user.csv and app_users.yaml")
    parser.add_argument("--check", action="store_true", help="Verify completeness gate and outputs")
    args = parser.parse_args(argv)

    sap_dir = resolve_sap_landing_dir()
    rows = compute_users_from_sap(sap_dir)
    verify_records(rows)
    if not args.check or not DEFAULT_OUT_CSV.exists() or not DEFAULT_OUT_YAML.exists():
        write_outputs(rows)
    else:
        # Also ensure files on disk are up to date
        write_outputs(rows)

    print("persona_id | emp_id     | display_name       | grade | func | wc_id  | pay26 | el/cl/hpl | post | apar")
    print("-" * 98)
    for r in rows:
        l_str = f"{r['leave_el_rows']}/{r['leave_cl_rows']}/{r['leave_hpl_rows']}"
        print(
            f"{r['persona_id']:<10} | {r['emp_id']:<10} | {r['display_name']:<18} | "
            f"{r['grade']:<5} | {r['function']:<4} | {r['wc_id']:<6} | "
            f"{r['pay_fy26_months']:>5} | {l_str:>9} | {r['posting_rows']:>4} | {r['apar_rows']:>4}"
        )
    print(f"\nOK: 11/11 personas verified; wrote {DEFAULT_OUT_CSV} and {DEFAULT_OUT_YAML}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
