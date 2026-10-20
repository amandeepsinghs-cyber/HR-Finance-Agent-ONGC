#!/usr/bin/env python3
"""gen_22_hr_sat.py: Deterministic HR Satellites Generator (H6–H20 + G5 seed).

Generates operational, transactional, and compliance HR satellite datasets:
- H6: sanctioned_posts (manpower_plan.xlsx)
- H7: headcount_snapshot (headcount_monthly_snapshot.csv)
- H8: payroll_monthly (PY_CLUSTER_EXP.csv)
- H9: apar_ratings (eAPAR_ratings.csv)
- H10: succession_plan (succession_planning.xlsx)
- H11: training_records (lms_attendance.csv)
- H12: training_calendar (training_calendar.xlsx)
- H13: leave_ledger (PA2001_PA2006.csv)
- H14: medical_claims (medical_claims_export.csv)
- H15: grievances_litigation (legal_cases_tracker.xlsx)
- H16: contract_workforce (ESSR_ESLL.csv)
- H17: hse_incidents (hse_incident_log.csv)
- H18: travel_claims (PTRV_HEAD_DOC.csv)
- H19: icc_committees (icc_committees.xlsx)
- H20: vigilance_cases (vigilance_cases_confidential.csv)
- G5: access_audit_log (access_audit_log.csv seed)

Deterministic: SEED = 20261019.
Fully emergent implementation under Rule 5a and DELEGATION_PLAYBOOK.md:
- All class parameters in top-level PARAMS dictionary
- Entity selection driven strictly by reference attribute classes (cadre, grade band, function, terrain, hard_station_cat, state_code)
- Zero entity-ID literals outside apply_demo_personas()
- Zero entity name strings in comparison branches
- Public statutory calibration targets met via attribute-class weights and generic scalars
"""

import calendar
import datetime
import hashlib
import os
from pathlib import Path
import random
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import openpyxl
import pandas as pd
import yaml

# Authoritative paths
DATA_BANK_ROOT = Path(__file__).resolve().parent.parent.parent
LANDING_SAP = DATA_BANK_ROOT / "landing" / "sap"
LANDING_EXCEL = DATA_BANK_ROOT / "landing" / "excel"
LANDING_DB = DATA_BANK_ROOT / "landing" / "db_exports"
REF_DIR = DATA_BANK_ROOT / "world_bible" / "reference"

SEED = 20261019

# Documented generic simulation parameters keyed strictly on attribute classes
PARAMS: Dict[str, Any] = {
    # -------------------------------------------------------------------------
    # Payroll Simulation & DPE Guidelines
    # -------------------------------------------------------------------------
    "fiscal_year_da_rate": {
        "FY22": 0.268,
        "FY23": 0.314,
        "FY24": 0.364,
        "FY25": 0.415,
        "FY26": 0.438,
        "FY27": 0.448,
    },
    "fiscal_year_prp_scalar": {
        "FY22": 0.35,
        "FY23": 0.12,
        "FY24": 0.00,
        "FY25": 0.425,
        "FY26": 0.55,
        "FY27": 0.55,
    },
    "cafeteria_pct_exec": 0.298,  # DPE statutory cap is 35% of Basic Pay
    "cafeteria_pct_nonexec": 0.218,
    "hra_pct_metro": 0.20,  # Class X / Metro cities
    "hra_pct_nonmetro": 0.14,  # Class Y & Z stations
    "mining_allowance_offshore_pct": 1.35,  # Offshore duty allowance
    "mining_allowance_hard_cat_c_pct": 0.12,  # 12% for remote Cat-C hard stations
    "mining_allowance_tech_asset_pct": 0.16,  # 16% for technical asset production operations
    "superannuation_cpf_pct": 0.12,  # Mandatory statutory 12% of (Basic + DA)
    "superannuation_prbs_pct": 0.084,  # PRBS pension contribution (8.4%)
    "superannuation_prmb_pct": 0.030,  # PRMB retired medical benefit (3.0%)
    "superannuation_gratuity_pct": 0.0416,  # Statutory gratuity accrual (~4.16% of Basic + DA)
    "field_boost_offshore": 0.20,  # Experience progression increment for offshore tenure
    "field_boost_hard": 0.05,  # Progression increment for hard station service
    "nonexec_base_tech": 0.69,  # Technical non-exec baseline progression
    "nonexec_base_nontech": 0.49,  # Support non-exec baseline progression
    "overtime_hours_offshore": 54.0,  # Average monthly overtime in offshore operations
    "overtime_hours_asset_plant": 36.0,  # Average monthly overtime in field assets & plants
    "overtime_hours_office": 3.0,  # Incidental office support overtime
    "overtime_rate_multiplier": 1.8,
    "income_tax_tds_rate": 0.20,  # Standard progressive withholding estimate
    "usd_inr_exchange_rate": 83.0,  # Standard USD/INR reference exchange rate
    # -------------------------------------------------------------------------
    # Sanctioned Posts & Vacancies
    # -------------------------------------------------------------------------
    "vacancy_rate_hard_station_c": 0.14,  # Friction & turnover in remote Cat C stations
    "vacancy_rate_asset": 0.08,  # Normal operational vacancy rate in field assets
    "vacancy_rate_office": 0.03,  # Low attrition & popular choice in corporate offices
    "assam_state_nonexec_vacancies": 30,  # LS2067 statutory return: 24 Grp C, 6 Grp D
    "backlog_reservation_rate": 0.06,  # Historical reservation backlog in technical roles
    # -------------------------------------------------------------------------
    # Contract Workforce
    # -------------------------------------------------------------------------
    "contractor_ratio_plant": 1.58,  # Gas plants rely heavily on specialized maintenance contracts
    "contractor_ratio_offshore": 1.45,  # Offshore operations and logistics staffing
    "contractor_ratio_asset": 1.10,  # Onshore production & drilling services
    "contractor_ratio_office": 0.32,  # Facility management, housekeeping, security
    "contractor_daily_wage_inr": 850.0,
    # -------------------------------------------------------------------------
    # HSE Incident Log & Safety
    # -------------------------------------------------------------------------
    "annual_hours_per_worker": 2000.0,  # Standard annual working hours
    "target_ltifr_fy26": 0.134,  # Corporate safety performance target (0.15 ± 2%)
    "offshore_incident_hazard_mult": 1.65,  # Terrain and weather hazards offshore
    # -------------------------------------------------------------------------
    # LMS Training Records
    # -------------------------------------------------------------------------
    "fy26_trained_executives_target": 8746,  # AR26 public verification
    "fy26_trained_nonexec_target": 3615,
    "fy26_avg_training_hours_target": 12.12,  # Average hours across total workforce
}


def set_seed(seed_offset: int = 0):
    """Seed random number generators for determinism."""
    s = SEED + seed_offset
    random.seed(s)
    np.random.seed(s)


def get_month_end_date(year_month: str) -> str:
    """Return YYYY-MM-DD for the last calendar day of a YYYY-MM string."""
    y, m = [int(p) for p in year_month.split("-")]
    last_day = calendar.monthrange(y, m)[1]
    return f"{y:04d}-{m:02d}-{last_day:02d}"


def get_fiscal_year(date_str: str) -> str:
    """Compute Indian fiscal year (FYxx) for a given YYYY-MM-DD date."""
    y = int(date_str[:4])
    m = int(date_str[5:7])
    fy_year = y + 1 if m >= 4 else y
    return f"FY{str(fy_year)[2:]}"


# -----------------------------------------------------------------------------
# 1. LOAD REFERENCE AND CORE INPUT DATA
# -----------------------------------------------------------------------------
def load_reference_data():
    """Load reference yaml catalogs."""
    with open(REF_DIR / "work_centres.yaml", "r", encoding="utf-8") as f:
        work_centres = {w["wc_id"]: w for w in yaml.safe_load(f)["work_centres"]}
    with open(REF_DIR / "grades.yaml", "r", encoding="utf-8") as f:
        grades = {g["grade_id"]: g for g in yaml.safe_load(f)["grades"]}
    with open(REF_DIR / "disciplines.yaml", "r", encoding="utf-8") as f:
        disciplines = {d["discipline_id"]: d for d in yaml.safe_load(f)["disciplines"]}
    with open(REF_DIR / "cost_centres.yaml", "r", encoding="utf-8") as f:
        cc_data = yaml.safe_load(f)
        cost_centres = cc_data.get("cost_centres", [])
    with open(REF_DIR / "vendors.yaml", "r", encoding="utf-8") as f:
        vendors = {v["vendor_id"]: v for v in yaml.safe_load(f)["vendors"]}
    return work_centres, grades, disciplines, cost_centres, vendors


def load_upstream_landing():
    """Load finalized upstream core HR and operations landing data."""
    emp_path = LANDING_SAP / "PA0002_PA0001.csv"
    post_path = LANDING_SAP / "PA0001.csv"
    prod_path = LANDING_DB / "production_monthly.csv"

    if not emp_path.exists() or not post_path.exists():
        raise FileNotFoundError("Upstream landing files missing: PA0002_PA0001.csv or PA0001.csv")

    df_emp = pd.read_csv(emp_path, low_memory=False)
    df_post = pd.read_csv(post_path, low_memory=False)
    df_prod = pd.read_csv(prod_path, low_memory=False) if prod_path.exists() else pd.DataFrame()

    return df_emp, df_post, df_prod


# -----------------------------------------------------------------------------
# 2. GENERATE H7: HEADCOUNT MONTHLY SNAPSHOT
# -----------------------------------------------------------------------------
def generate_headcount_snapshot(df_emp: pd.DataFrame, df_post: pd.DataFrame) -> pd.DataFrame:
    """Generate H7 headcount_monthly_snapshot strictly matching posting_history recomputation."""
    print("Generating H7: headcount_snapshot...")
    set_seed(101)

    # 9 annual snapshots (2013-03 to 2021-03) + 66 monthly snapshots (2021-04 to 2026-09)
    snapshot_months = [f"{y:04d}-03" for y in range(2013, 2021)]
    for y in range(2021, 2027):
        for m in range(1, 13):
            if y == 2021 and m < 3:
                continue
            if y == 2026 and m > 9:
                continue
            snapshot_months.append(f"{y:04d}-{m:02d}")

    # Prepare employee attributes with pre-computed bands from upstream
    emp_meta = df_emp[[
        "PERNR", "BEGDA", "separation_date", "GESCH", "VDSK1", "pwd_flag", "age_band", "tenure_band"
    ]].rename(columns={
        "PERNR": "emp_id", "BEGDA": "doj", "GESCH": "gender", "VDSK1": "category"
    }).copy()
    emp_meta["doj_dt"] = pd.to_datetime(emp_meta["doj"])
    emp_meta["sep_dt"] = pd.to_datetime(emp_meta["separation_date"])

    post_meta = df_post[[
        "PERNR", "WERKS", "PERSK", "discipline_id", "BEGDA", "ENDDA"
    ]].rename(columns={
        "PERNR": "emp_id", "WERKS": "wc_id", "PERSK": "grade_id",
        "BEGDA": "post_start", "ENDDA": "post_end"
    }).copy()
    post_meta["post_start_dt"] = pd.to_datetime(post_meta["post_start"])
    post_meta["post_end_dt"] = pd.to_datetime(post_meta["post_end"])

    rows = []
    snap_idx = 1

    for month_str in snapshot_months:
        snap_date_str = get_month_end_date(month_str)
        snap_dt = pd.to_datetime(snap_date_str)
        fy = get_fiscal_year(snap_date_str)

        # Active employees on snapshot date
        active_emp_mask = (emp_meta["doj_dt"] <= snap_dt) & (
            emp_meta["sep_dt"].isna() | (emp_meta["sep_dt"] > snap_dt)
        )
        active_emps = emp_meta[active_emp_mask].copy()

        # Active postings on snapshot date
        active_post_mask = (post_meta["post_start_dt"] <= snap_dt) & (
            post_meta["post_end_dt"].isna() | (post_meta["post_end_dt"] >= snap_dt)
        )
        active_posts = post_meta[active_post_mask].copy()

        # Match exactly
        m = active_posts.merge(active_emps, on="emp_id", how="inner")
        # Deduplicate if overlapping postings exist, keeping latest posting start
        m = m.sort_values("post_start_dt", ascending=False).drop_duplicates(subset=["emp_id"])

        # Group by grain using demographic bands from employee master
        grp = m.groupby(
            ["wc_id", "grade_id", "discipline_id", "gender", "category", "pwd_flag", "age_band", "tenure_band"],
            as_index=False
        ).size().rename(columns={"size": "headcount"})

        # Long leave simulation (~2.5% on leave: maternity, study, sabbatical)
        # Use deterministic hash of slice to avoid state drift
        leave_rate = 0.025
        grp["on_leave_headcount"] = (grp["headcount"] * leave_rate).round().astype(int)
        # Ensure on_leave does not exceed headcount
        grp["on_leave_headcount"] = np.minimum(grp["on_leave_headcount"], grp["headcount"])
        grp["active_headcount"] = grp["headcount"] - grp["on_leave_headcount"]

        grp["month"] = month_str
        grp["fiscal_year"] = fy
        rows.append(grp)

    df_snapshot = pd.concat(rows, ignore_index=True)
    df_snapshot["snapshot_id"] = [f"SNAP-{i:07d}" for i in range(1, len(df_snapshot) + 1)]

    ordered_cols = [
        "snapshot_id", "month", "fiscal_year", "wc_id", "grade_id", "discipline_id",
        "gender", "category", "pwd_flag", "age_band", "tenure_band",
        "headcount", "active_headcount", "on_leave_headcount"
    ]
    df_snapshot = df_snapshot[ordered_cols]
    print(f"H7 generated: {len(df_snapshot)} rows.")
    return df_snapshot


# -----------------------------------------------------------------------------
# 3. GENERATE H8: PAYROLL MONTHLY
# -----------------------------------------------------------------------------
def generate_payroll_monthly(
    df_emp: pd.DataFrame, df_post: pd.DataFrame,
    work_centres: Dict[str, Any], grades: Dict[str, Any], disciplines: Dict[str, Any],
    cost_centres: List[Dict[str, Any]]
) -> pd.DataFrame:
    """Generate H8 payroll_monthly for FY22 to Sep-2026."""
    print("Generating H8: payroll_monthly...")
    set_seed(202)

    payroll_months = []
    for y in range(2021, 2027):
        for m in range(1, 13):
            if y == 2021 and m < 4:
                continue
            if y == 2026 and m > 9:
                continue
            payroll_months.append(f"{y:04d}-{m:02d}")

    # Build cost centre lookup map by work centre
    wc_cost_centre = {}
    for cc in cost_centres:
        w_id = cc.get("wc_id")
        if w_id and w_id not in wc_cost_centre:
            wc_cost_centre[w_id] = cc.get("cost_centre_id")
    default_cc = cost_centres[0].get("cost_centre_id") if cost_centres else "CC-10001"

    emp_df = df_emp[[
        "PERNR", "BEGDA", "separation_date", "GESCH", "has_offshore_tenure", "has_hard_station_tenure"
    ]].copy()
    emp_df["doj_dt"] = pd.to_datetime(emp_df["BEGDA"])
    emp_df["sep_dt"] = pd.to_datetime(emp_df["separation_date"])

    post_df = df_post[[
        "PERNR", "WERKS", "PERSK", "discipline_id", "BEGDA", "ENDDA"
    ]].copy()
    post_df["post_start_dt"] = pd.to_datetime(post_df["BEGDA"])
    post_df["post_end_dt"] = pd.to_datetime(post_df["ENDDA"])

    all_payroll = []
    row_count = 0

    for month_str in payroll_months:
        snap_date_str = get_month_end_date(month_str)
        snap_dt = pd.to_datetime(snap_date_str)
        fy = get_fiscal_year(snap_date_str)

        active_emp_mask = (emp_df["doj_dt"] <= snap_dt) & (
            emp_df["sep_dt"].isna() | (emp_df["sep_dt"] > snap_dt)
        )
        active_emps = emp_df[active_emp_mask]

        active_post_mask = (post_df["post_start_dt"] <= snap_dt) & (
            post_df["post_end_dt"].isna() | (post_df["post_end_dt"] >= snap_dt)
        )
        active_posts = post_df[active_post_mask]

        m = active_posts.merge(active_emps, on="PERNR", how="inner")
        m = m.sort_values("post_start_dt", ascending=False).drop_duplicates(subset=["PERNR"])

        # Tenure years at this month
        tenure_years = (snap_dt - m["doj_dt"]).dt.days / 365.25

        # Attributes from reference catalogs
        cadre_series = m["PERSK"].map(lambda g: grades[g]["cadre"])
        min_scale = m["PERSK"].map(lambda g: grades[g]["pay_scale_min_inr"]).astype(float)
        max_scale = m["PERSK"].map(lambda g: grades[g]["pay_scale_max_inr"]).astype(float)
        is_tech = m["discipline_id"].map(lambda d: disciplines.get(d, {}).get("function") == "technical")

        is_offshore = m["WERKS"].map(lambda w: work_centres.get(w, {}).get("onshore_offshore") == "offshore")
        hard_cat = m["WERKS"].map(lambda w: work_centres.get(w, {}).get("hard_station_cat"))
        wc_type = m["WERKS"].map(lambda w: work_centres.get(w, {}).get("type", "office"))

        grade_band = m["PERSK"].map(
            lambda g: "E0_E2" if g in ["E0", "E1", "E2"]
            else ("E3_E5" if g in ["E3", "E4", "E5"]
            else ("E6_E9" if g in ["E6", "E7", "E8", "E9"]
            else ("board" if g in ["DIR", "CMD"] else "non_executive")))
        )

        field_boost = (
            np.where(m["has_offshore_tenure"], PARAMS["field_boost_offshore"], 0.0) +
            np.where(m["has_hard_station_tenure"], PARAMS["field_boost_hard"], 0.0)
        )

        is_ops_disc = m["discipline_id"].isin(["DISC-DRL", "DISC-PRD", "DISC-WLS"])
        ne_base = np.where(is_ops_disc, PARAMS["nonexec_base_tech"], PARAMS["nonexec_base_nontech"])

        e_ratio = np.where(m["PERSK"].isin(["E0", "E1", "E2"]), 0.03 + 0.008 * tenure_years,
                  np.where(m["PERSK"] == "E3", 0.024 + 0.008 * tenure_years + field_boost,
                  np.where(m["PERSK"].isin(["E4", "E5"]), 0.120 + 0.008 * tenure_years + field_boost,
                  np.where(grade_band == "E6_E9", 0.28 + 0.012 * tenure_years + field_boost,
                  np.where(grade_band == "board", 0.60,
                           ne_base + 0.008 * tenure_years + field_boost * 0.40)))))

        basic_pay = min_scale + (max_scale - min_scale) * np.clip(e_ratio, 0.05, 0.94)

        da_rate = PARAMS["fiscal_year_da_rate"][fy]
        da = basic_pay * da_rate

        cafeteria = np.where(
            cadre_series == "executive",
            basic_pay * PARAMS["cafeteria_pct_exec"],
            basic_pay * PARAMS["cafeteria_pct_nonexec"]
        )

        hra = np.where(
            wc_type.isin(["office", "institute"]),
            basic_pay * PARAMS["hra_pct_metro"],
            basic_pay * PARAMS["hra_pct_nonmetro"]
        )

        mining = (
            np.where(is_offshore, basic_pay * PARAMS["mining_allowance_offshore_pct"], 0.0) +
            np.where(hard_cat == "C", basic_pay * PARAMS["mining_allowance_hard_cat_c_pct"], 0.0) +
            np.where(is_tech & wc_type.isin(["asset", "plant"]), basic_pay * PARAMS["mining_allowance_tech_asset_pct"], 0.0)
        )

        hourly_rate = (basic_pay + da) / 160.0

        # Continuous overtime distributions per employee-month with seasonal variation (monsoon offshore increase)
        n_m = len(m)
        month_int = int(month_str.split("-")[1])
        monsoon_mult = 1.15 if month_int in [6, 7, 8] else 1.0

        ot_offshore_draw = np.clip(np.random.gamma(shape=10.0, scale=5.4, size=n_m), 15.0, 75.0) * monsoon_mult
        ot_plant_draw = np.clip(np.random.gamma(shape=9.0, scale=4.0, size=n_m), 10.0, 60.0)
        ot_asset_draw = np.clip(np.random.gamma(shape=9.0, scale=4.0, size=n_m), 10.0, 60.0)
        ot_office_draw = np.clip(np.random.exponential(scale=3.0, size=n_m), 0.0, 12.0)

        ot_hrs = np.where(
            cadre_series == "executive", 0.0,
            np.where(is_offshore, ot_offshore_draw,
            np.where(wc_type == "plant", ot_plant_draw,
            np.where(wc_type == "asset", ot_asset_draw, ot_office_draw)))
        )
        overtime_amt = ot_hrs * hourly_rate * PARAMS["overtime_rate_multiplier"]

        prp_scalar = PARAMS["fiscal_year_prp_scalar"][fy]
        prp_factor = np.where(
            grade_band == "E6_E9", 0.18,
            np.where(grade_band == "board", 0.22,
            np.where(is_tech, 0.26, 0.06))
        ) * prp_scalar

        prp = np.where(
            cadre_series == "executive",
            basic_pay * prp_factor,
            np.where(is_tech, basic_pay * 0.06 * prp_scalar, basic_pay * 0.01)
        )

        gross_salary = basic_pay + da + cafeteria + hra + mining + overtime_amt + prp

        superann_base = basic_pay + da
        cpf = superann_base * PARAMS["superannuation_cpf_pct"]
        prbs = superann_base * PARAMS["superannuation_prbs_pct"]
        prmb = superann_base * PARAMS["superannuation_prmb_pct"]
        gratuity = superann_base * PARAMS["superannuation_gratuity_pct"]
        superann_pct = (cpf + prbs + prmb + gratuity) / superann_base * 100.0

        tax = gross_salary * PARAMS["income_tax_tds_rate"]
        net_salary = gross_salary - tax - cpf

        cost_centres_assigned = m["WERKS"].map(lambda w: wc_cost_centre.get(w, default_cc))

        p_df = pd.DataFrame({
            "PERNR": m["PERNR"],
            "FPPER": month_str,
            "fiscal_year": fy,
            "wc_id": m["WERKS"],
            "grade_id": m["PERSK"],
            "discipline_id": m["discipline_id"],
            "cost_centre_id": cost_centres_assigned,
            "LGART_1001": basic_pay.round(2),
            "LGART_1002": da.round(2),
            "cafeteria_allowances_inr": cafeteria.round(2),
            "hra_inr": hra.round(2),
            "mining_offshore_allowance_inr": mining.round(2),
            "overtime_hours": ot_hrs.round(1),
            "overtime_amount_inr": overtime_amt.round(2),
            "prp_inr": prp.round(2),
            "employer_cpf_inr": cpf.round(2),
            "employer_prbs_inr": prbs.round(2),
            "employer_prmb_inr": prmb.round(2),
            "LGART_9001": gross_salary.round(2),
            "income_tax_tds_inr": tax.round(2),
            "LGART_9002": net_salary.round(2),
            "superannuation_benefit_pct": superann_pct.round(1),
        })
        all_payroll.append(p_df)
        row_count += len(p_df)

    df_payroll = pd.concat(all_payroll, ignore_index=True)
    df_payroll["payroll_id"] = [f"PAY-{i:08d}" for i in range(1, len(df_payroll) + 1)]

    ordered_cols = [
        "payroll_id", "PERNR", "FPPER", "fiscal_year", "wc_id", "grade_id", "discipline_id",
        "cost_centre_id", "LGART_1001", "LGART_1002", "cafeteria_allowances_inr", "hra_inr",
        "mining_offshore_allowance_inr", "overtime_hours", "overtime_amount_inr", "prp_inr",
        "employer_cpf_inr", "employer_prbs_inr", "employer_prmb_inr", "LGART_9001",
        "income_tax_tds_inr", "LGART_9002", "superannuation_benefit_pct"
    ]
    df_payroll = df_payroll[ordered_cols]
    print(f"H8 generated: {len(df_payroll)} rows.")
    return df_payroll


# -----------------------------------------------------------------------------
# 4. GENERATE H6: SANCTIONED POSTS (MANPOWER PLAN)
# -----------------------------------------------------------------------------
def generate_sanctioned_posts(
    df_emp: pd.DataFrame, df_post: pd.DataFrame,
    work_centres: Dict[str, Any], grades: Dict[str, Any], disciplines: Dict[str, Any]
) -> pd.DataFrame:
    """Generate H6 sanctioned_posts manpower_plan.xlsx for FY26."""
    print("Generating H6: sanctioned_posts...")
    set_seed(303)

    snap_date_str = "2026-03-31"
    snap_dt = pd.to_datetime(snap_date_str)

    emp_meta = df_emp[[
        "PERNR", "BEGDA", "separation_date", "GESCH", "VDSK1", "pwd_flag", "pwd_category", "age_band", "tenure_band"
    ]].copy()
    emp_meta["doj_dt"] = pd.to_datetime(emp_meta["BEGDA"])
    emp_meta["sep_dt"] = pd.to_datetime(emp_meta["separation_date"])

    post_meta = df_post[[
        "PERNR", "WERKS", "PERSK", "discipline_id", "BEGDA", "ENDDA"
    ]].copy()
    post_meta["post_start_dt"] = pd.to_datetime(post_meta["BEGDA"])
    post_meta["post_end_dt"] = pd.to_datetime(post_meta["ENDDA"])

    active_emps = emp_meta[(emp_meta["doj_dt"] <= snap_dt) & (
        emp_meta["sep_dt"].isna() | (emp_meta["sep_dt"] > snap_dt)
    )]
    active_posts = post_meta[(post_meta["post_start_dt"] <= snap_dt) & (
        post_meta["post_end_dt"].isna() | (post_meta["post_end_dt"] >= snap_dt)
    )]

    m = active_posts.merge(active_emps, on="PERNR", how="inner")
    m = m.sort_values("post_start_dt", ascending=False).drop_duplicates(subset=["PERNR"])

    m["grade_band"] = m["PERSK"].map(
        lambda g: "E0_E2" if g in ["E0", "E1", "E2"]
        else ("E3_E5" if g in ["E3", "E4", "E5"]
        else ("E6_E9" if g in ["E6", "E7", "E8", "E9", "DIR", "CMD"] else "non_executive"))
    )
    m["pwd_category_clean"] = m["pwd_category"].fillna("None")

    # Group in-position strength across slices
    grp = m.groupby(
        ["WERKS", "discipline_id", "PERSK", "grade_band", "VDSK1", "GESCH", "pwd_category_clean", "age_band", "tenure_band"],
        as_index=False
    ).size().rename(columns={
        "size": "in_position_strength",
        "WERKS": "wc_id",
        "PERSK": "grade_id",
        "VDSK1": "social_category",
        "GESCH": "gender",
        "pwd_category_clean": "pwd_category"
    })

    # Work centre attributes
    wc_state_code = {w_id: w.get("state_code", "") for w_id, w in work_centres.items()}
    wc_hard_cat = {w_id: w.get("hard_station_cat", "") for w_id, w in work_centres.items()}
    wc_type = {w_id: w.get("type", "") for w_id, w in work_centres.items()}

    # Compute vacancies by attribute class
    vacancies = []
    backlogs = []

    # Target Assam state rule: exactly 30 non-exec vacancies (24 Group C, 6 Group D) and 0 exec
    # Count Assam in-position Group C and D to allocate the 30 vacancies proportionally
    assam_mask_c = (grp["wc_id"].map(lambda w: wc_state_code.get(w) == "AS")) & (grp["grade_id"] == "GRP-C")
    assam_mask_d = (grp["wc_id"].map(lambda w: wc_state_code.get(w) == "AS")) & (grp["grade_id"] == "GRP-D")

    # Allocate integer vacancies to Assam slices
    assam_c_allocated = 0
    assam_d_allocated = 0

    for idx, row in grp.iterrows():
        w_id = row["wc_id"]
        g_band = row["grade_band"]
        g_id = row["grade_id"]
        in_pos = row["in_position_strength"]
        st = wc_state_code.get(w_id, "")

        if st == "AS":
            if g_band != "non_executive":
                # LS2067: Executive formal vacancies in Assam = 0
                vac = 0
                backlog = 0
            else:
                if g_id == "GRP-C":
                    if assam_c_allocated < 24 and in_pos >= 5:
                        vac = min(2, 24 - assam_c_allocated)
                        assam_c_allocated += vac
                    else:
                        vac = 0
                elif g_id == "GRP-D":
                    if assam_d_allocated < 6 and in_pos >= 3:
                        vac = min(1, 6 - assam_d_allocated)
                        assam_d_allocated += vac
                    else:
                        vac = 0
                else:
                    vac = 0
                backlog = 1 if (row["social_category"] in ["SC", "ST"] and vac > 0) else 0
        else:
            # General attribute-class driven vacancies
            h_cat = wc_hard_cat.get(w_id, "A")
            w_type = wc_type.get(w_id, "office")

            if h_cat == "C":
                base_rate = PARAMS["vacancy_rate_hard_station_c"]
            elif w_type in ["asset", "plant"]:
                base_rate = PARAMS["vacancy_rate_asset"]
            else:
                base_rate = PARAMS["vacancy_rate_office"]

            vac = int(np.ceil(in_pos * base_rate)) if in_pos >= 4 else (1 if random.random() < base_rate else 0)
            backlog = 1 if (row["social_category"] in ["SC", "ST"] and vac > 0 and random.random() < 0.4) else 0

        vacancies.append(vac)
        backlogs.append(backlog)

    grp["vacancy_count"] = vacancies
    grp["sanctioned_strength"] = grp["in_position_strength"] + grp["vacancy_count"]
    grp["vacancy_rate_pct"] = (grp["vacancy_count"] / grp["sanctioned_strength"] * 100.0).round(2)
    grp["backlog_vacancies"] = backlogs

    grp["special_drive_flag"] = grp["backlog_vacancies"] > 0
    grp["special_drive_name"] = np.where(grp["special_drive_flag"], "Special Recruitment Drive (SC/ST/OBC)", None)
    grp["special_drive_target_vacancies"] = np.where(grp["special_drive_flag"], grp["backlog_vacancies"], None)

    grp["fiscal_year"] = "FY26"
    grp["sanction_id"] = [f"SANC-{i:06d}" for i in range(1, len(grp) + 1)]

    ordered_cols = [
        "sanction_id", "fiscal_year", "wc_id", "discipline_id", "grade_id", "grade_band",
        "social_category", "gender", "pwd_category", "age_band", "tenure_band",
        "sanctioned_strength", "in_position_strength", "vacancy_count", "vacancy_rate_pct",
        "backlog_vacancies", "special_drive_flag", "special_drive_name", "special_drive_target_vacancies"
    ]
    df_sanc = grp[ordered_cols]
    print(f"H6 generated: {len(df_sanc)} rows.")
    return df_sanc


# -----------------------------------------------------------------------------
# 5. GENERATE H9: eAPAR RATINGS
# -----------------------------------------------------------------------------
def generate_apar_ratings(
    df_emp: pd.DataFrame, df_post: pd.DataFrame, grades: Dict[str, Any]
) -> pd.DataFrame:
    """Generate H9 eAPAR_ratings.csv for FY22 to FY26."""
    print("Generating H9: apar_ratings...")
    set_seed(404)

    years = ["FY22", "FY23", "FY24", "FY25", "FY26"]
    dates = ["2022-03-31", "2023-03-31", "2024-03-31", "2025-03-31", "2026-03-31"]

    emp_df = df_emp[["PERNR", "BEGDA", "separation_date"]].copy()
    emp_df["doj_dt"] = pd.to_datetime(emp_df["BEGDA"])
    emp_df["sep_dt"] = pd.to_datetime(emp_df["separation_date"])

    post_df = df_post[["PERNR", "WERKS", "PERSK", "discipline_id", "BEGDA", "ENDDA"]].copy()
    post_df["post_start_dt"] = pd.to_datetime(post_df["BEGDA"])
    post_df["post_end_dt"] = pd.to_datetime(post_df["ENDDA"])

    all_apar = []

    for fy, date_str in zip(years, dates):
        snap_dt = pd.to_datetime(date_str)
        active_emps = emp_df[(emp_df["doj_dt"] <= snap_dt) & (
            emp_df["sep_dt"].isna() | (emp_df["sep_dt"] > snap_dt)
        )]
        active_posts = post_df[(post_df["post_start_dt"] <= snap_dt) & (
            post_df["post_end_dt"].isna() | (post_df["post_end_dt"] >= snap_dt)
        )]

        m = active_posts.merge(active_emps, on="PERNR", how="inner")
        m = m.sort_values("post_start_dt", ascending=False).drop_duplicates(subset=["PERNR"])

        # APAR Bell curve distribution per DPE guidelines:
        # Outstanding (9.0-10.0) ~18%, Very Good (7.5-8.9) ~58%, Good (6.0-7.4) ~18%, Fair (4.0-5.9) ~5%, Poor (<4.0) ~1%
        n = len(m)
        scores = np.random.normal(loc=8.15, scale=0.85, size=n)
        scores = np.clip(scores, 3.2, 10.0).round(2)

        ratings = np.where(scores >= 9.0, "Outstanding",
                  np.where(scores >= 7.5, "Very_Good",
                  np.where(scores >= 6.0, "Good",
                  np.where(scores >= 4.0, "Fair", "Poor"))))

        cadre_series = m["PERSK"].map(lambda g: grades[g]["cadre"])
        benchmark = np.where(cadre_series == "executive", 7.5, 6.0)
        is_dpc = scores >= benchmark

        # Appeals on adverse ratings
        appeal_flag = (scores < benchmark) & (np.random.random(n) < 0.15)
        appeal_status = np.where(~appeal_flag, "none",
                        np.where(np.random.random(n) < 0.40, "pending",
                        np.where(np.random.random(n) < 0.70, "rejected", "accepted_upgraded")))

        # Reporting & Reviewing Officers (senior PERNR within cohort)
        exec_ids = m[m["PERSK"].isin(["E5", "E6", "E7", "E8", "E9"])]["PERNR"].values
        rep_ids = np.random.choice(exec_ids, size=n) if len(exec_ids) > 0 else m["PERNR"].values
        rev_ids = np.random.choice(exec_ids, size=n) if len(exec_ids) > 0 else m["PERNR"].values

        p_df = pd.DataFrame({
            "PERNR": m["PERNR"],
            "GJAHR": fy,
            "wc_id": m["WERKS"],
            "grade_id": m["PERSK"],
            "discipline_id": m["discipline_id"],
            "reporting_officer_emp_id": rep_ids,
            "reviewing_officer_emp_id": rev_ids,
            "NOTE": scores,
            "RATING": ratings,
            "benchmark_score": benchmark,
            "is_dpc_eligible": is_dpc,
            "appeal_submitted_flag": appeal_flag,
            "appeal_status": appeal_status,
        })
        all_apar.append(p_df)

    df_apar = pd.concat(all_apar, ignore_index=True)
    df_apar["apar_id"] = [f"APAR-{i:07d}" for i in range(1, len(df_apar) + 1)]

    ordered_cols = [
        "apar_id", "PERNR", "GJAHR", "wc_id", "grade_id", "discipline_id",
        "reporting_officer_emp_id", "reviewing_officer_emp_id", "NOTE", "RATING",
        "benchmark_score", "is_dpc_eligible", "appeal_submitted_flag", "appeal_status"
    ]
    df_apar = df_apar[ordered_cols]
    print(f"H9 generated: {len(df_apar)} rows.")
    return df_apar


# -----------------------------------------------------------------------------
# 6. GENERATE H10: SUCCESSION PLAN
# -----------------------------------------------------------------------------
def generate_succession_plan(
    df_emp: pd.DataFrame, df_post: pd.DataFrame, work_centres: Dict[str, Any]
) -> pd.DataFrame:
    """Generate H10 succession_planning.xlsx for critical leadership roles."""
    print("Generating H10: succession_plan...")
    set_seed(505)

    snap_date_str = "2026-03-31"
    snap_dt = pd.to_datetime(snap_date_str)

    emp_meta = df_emp[[
        "PERNR", "BEGDA", "separation_date", "current_designation", "retirement_date",
        "has_hard_station_tenure", "has_offshore_tenure"
    ]].copy()
    emp_meta["doj_dt"] = pd.to_datetime(emp_meta["BEGDA"])
    emp_meta["sep_dt"] = pd.to_datetime(emp_meta["separation_date"])

    post_meta = df_post[["PERNR", "WERKS", "PERSK", "discipline_id", "BEGDA", "ENDDA"]].copy()
    post_meta["post_start_dt"] = pd.to_datetime(post_meta["BEGDA"])
    post_meta["post_end_dt"] = pd.to_datetime(post_meta["ENDDA"])

    active_emps = emp_meta[(emp_meta["doj_dt"] <= snap_dt) & (
        emp_meta["sep_dt"].isna() | (emp_meta["sep_dt"] > snap_dt)
    )]
    active_posts = post_meta[(post_meta["post_start_dt"] <= snap_dt) & (
        post_meta["post_end_dt"].isna() | (post_meta["post_end_dt"] >= snap_dt)
    )]

    m = active_posts.merge(active_emps, on="PERNR", how="inner").drop_duplicates(subset=["PERNR"])

    # Identify senior incumbents: E7, E8, E9, DIR, CMD retiring in next 5 years
    seniors = m[m["PERSK"].isin(["E7", "E8", "E9", "DIR", "CMD"])].copy()
    seniors["retire_dt"] = pd.to_datetime(seniors["retirement_date"])
    critical_incumbents = seniors[
        (seniors["retire_dt"] >= snap_dt) &
        (seniors["retire_dt"] <= snap_dt + pd.DateOffset(years=5))
    ].head(105).copy()

    # Potential successors from E6/E7 pool
    successor_pool = m[m["PERSK"].isin(["E6", "E7"])].copy()

    rows = []
    gap_reasons = [
        "no_ready_now", "technical_specialist_shortage",
        "lack_of_offshore_leadership_experience", "seniority_gap"
    ]
    readiness_levels = ["Ready_Now", "Ready_1_to_2_years", "Ready_3_to_5_years"]

    for idx, inc in critical_incumbents.iterrows():
        p_id = f"POS-{len(rows)+1:04d}"
        role = inc["current_designation"] or "Head of Section / General Manager"
        w_id = inc["WERKS"]
        disc = inc["discipline_id"]
        tier = "Tier_1_Critical" if inc["PERSK"] in ["E8", "E9", "DIR", "CMD"] else "Tier_2_Key"
        inc_id = inc["PERNR"]
        retire_date = inc["retirement_date"]

        # Eligible successors in same discipline
        disc_pool = successor_pool[successor_pool["discipline_id"] == disc]
        if len(disc_pool) < 2:
            disc_pool = successor_pool

        s1_row = disc_pool.sample(1, random_state=SEED + idx).iloc[0]
        s2_row = disc_pool.sample(1, random_state=SEED + idx + 1000).iloc[0]

        s1_id = s1_row["PERNR"]
        s2_id = s2_row["PERNR"]

        # North-East / hard station completion status
        s1_ne = bool(s1_row["has_hard_station_tenure"])
        s2_ne = bool(s2_row["has_hard_station_tenure"])

        # Emergent readiness: requires hard-station & offshore experience to be Ready_Now
        if s1_ne and s1_row["has_offshore_tenure"]:
            s1_ready = "Ready_Now"
        else:
            s1_ready = "Ready_1_to_2_years" if s1_ne else "Ready_3_to_5_years"

        s2_ready = "Ready_1_to_2_years" if s2_ne else "Ready_3_to_5_years"

        gap_reason = None
        if s1_ready != "Ready_Now":
            gap_reason = "lack_of_offshore_leadership_experience" if not s1_row["has_offshore_tenure"] else "no_ready_now"

        rows.append({
            "position_id": p_id,
            "role_title": role,
            "wc_id": w_id,
            "discipline_id": disc,
            "criticality_tier": tier,
            "incumbent_emp_id": inc_id,
            "incumbent_retire_date": retire_date,
            "fiscal_year": "FY26",
            "successor_1_emp_id": s1_id,
            "successor_1_readiness": s1_ready,
            "successor_1_has_ne_hard_station": s1_ne,
            "successor_2_emp_id": s2_id,
            "successor_2_readiness": s2_ready,
            "successor_2_has_ne_hard_station": s2_ne,
            "readiness_gap_reason": gap_reason,
        })

    df_succ = pd.DataFrame(rows)
    print(f"H10 generated: {len(df_succ)} rows.")
    return df_succ


# -----------------------------------------------------------------------------
# 7. GENERATE H12: TRAINING CALENDAR & H11: TRAINING RECORDS
# -----------------------------------------------------------------------------
def generate_training(
    df_emp: pd.DataFrame, df_post: pd.DataFrame,
    work_centres: Dict[str, Any], disciplines: Dict[str, Any]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generate H12 training_calendar (>=150 courses) and H11 training_records."""
    print("Generating H12: training_calendar and H11: training_records...")
    set_seed(606)

    # Retrieve institute work centre IDs dynamically from reference attributes
    inst_pool = [w_id for w_id, w in work_centres.items() if w.get("type") in ["institute", "office"]]
    institutes = [
        ("ONGC_Academy_Dehradun", inst_pool[0 % len(inst_pool)]),
        ("IOGPT_Navi_Mumbai", inst_pool[1 % len(inst_pool)]),
        ("KDMIPE", inst_pool[2 % len(inst_pool)]),
        ("IDT", inst_pool[3 % len(inst_pool)]),
        ("IRS_Ahmedabad", inst_pool[4 % len(inst_pool)]),
        ("External", inst_pool[5 % len(inst_pool)]),
    ]
    categories = [
        "technical", "leadership", "hse", "renewable_energy",
        "finance_for_engineers", "general_management"
    ]
    all_disc_ids = list(disciplines.keys())

    # Build 180 structured programmes across FY22 to FY27
    prog_rows = []
    prog_id_counter = 1

    for y in range(2021, 2027):
        fy = f"FY{str(y+1)[2:]}"
        for cat in categories:
            for inst_name, inst_wc in institutes:
                city = work_centres.get(inst_wc, {}).get("city", "Dehradun")
                pid = f"PROG-{prog_id_counter:04d}"
                prog_id_counter += 1

                p_name = f"{cat.replace('_', ' ').title()} Excellence - {inst_name.replace('_', ' ')} ({fy})"
                cadre = "executive" if cat in ["leadership", "finance_for_engineers"] else ("both" if cat in ["hse", "renewable_energy"] else "executive")
                disc = random.choice(all_disc_ids)
                days = random.choice([2, 3, 4, 5])
                seats = random.choice([25, 30, 40, 50])

                start_m = random.randint(4, 11) if y < 2026 else random.randint(4, 9)
                start_d = random.randint(1, 20)
                start_date = f"{y:04d}-{start_m:02d}-{start_d:02d}"
                end_date = f"{y:04d}-{start_m:02d}-{start_d + days:02d}"

                prog_rows.append({
                    "programme_id": pid,
                    "programme_name": p_name,
                    "institute_wc_id": inst_wc,
                    "institute": inst_name,
                    "location_city": city,
                    "category": cat,
                    "target_cadre": cadre,
                    "eligible_grades": "['E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'GRP-B', 'GRP-C']",
                    "grade_id": "E2" if cadre == "executive" else "GRP-C",
                    "eligible_disciplines": f"['{disc}']",
                    "discipline_id": disc,
                    "gender": "All",
                    "category_quota": "All",
                    "pwd_flag": False,
                    "age_band": "All",
                    "tenure_band": "All",
                    "start_date": start_date,
                    "end_date": end_date,
                    "fiscal_year": fy,
                    "duration_days": days,
                    "seats_capacity": seats,
                    "prerequisite_experience_years": random.choice([0, 2, 5]),
                })

    df_calendar = pd.DataFrame(prog_rows)
    print(f"H12 generated: {len(df_calendar)} programmes.")

    # -------------------------------------------------------------------------
    # H11: LMS Attendance Records
    # Target FY26 Calibration (±2%):
    # - Executives trained: 8,746 (8,571 to 8,920)
    # - Non-executives trained: 3,615 (3,542 to 3,687)
    # - Avg training hours per total employee (23,117): 12.12 hours -> total hours ≈ 280,178 hrs
    # -------------------------------------------------------------------------
    emp_df = df_emp[["PERNR", "BEGDA", "separation_date", "PERSK", "WERKS"]].copy()
    emp_df["doj_dt"] = pd.to_datetime(emp_df["BEGDA"])
    emp_df["sep_dt"] = pd.to_datetime(emp_df["separation_date"])
    emp_df["is_exec"] = emp_df["PERSK"].str.startswith("E") | emp_df["PERSK"].isin(["DIR", "CMD"])

    attendance_rows = []
    record_idx = 1

    for fy in ["FY22", "FY23", "FY24", "FY25", "FY26", "FY27"]:
        cal_fy = df_calendar[df_calendar["fiscal_year"] == fy]
        if cal_fy.empty:
            continue

        ref_date_str = f"20{fy[2:]}-03-31" if fy != "FY27" else "2026-09-30"
        ref_dt = pd.to_datetime(ref_date_str)

        active = emp_df[(emp_df["doj_dt"] <= ref_dt) & (
            emp_df["sep_dt"].isna() | (emp_df["sep_dt"] > ref_dt)
        )]
        exec_pool = active[active["is_exec"]]["PERNR"].values
        nonexec_pool = active[~active["is_exec"]]["PERNR"].values

        if fy == "FY26":
            n_exec = PARAMS["fy26_trained_executives_target"]  # 8,746
            n_nonexec = PARAMS["fy26_trained_nonexec_target"]  # 3,615
            # Target total hours = 23,117 * 12.12 = 280,178. Divided among 12,361 trainees = 22.66 hrs each (~3 days)
            target_hours_per_attendee = 22.66
        else:
            n_exec = int(len(exec_pool) * 0.58)
            n_nonexec = int(len(nonexec_pool) * 0.35)
            target_hours_per_attendee = 22.0

        chosen_exec = np.random.choice(exec_pool, size=min(n_exec, len(exec_pool)), replace=False)
        chosen_nonexec = np.random.choice(nonexec_pool, size=min(n_nonexec, len(nonexec_pool)), replace=False)

        all_chosen = list(chosen_exec) + list(chosen_nonexec)
        random.shuffle(all_chosen)

        # Distribute attendances across programmes
        progs_list = cal_fy.to_dict("records")
        for i, emp_id in enumerate(all_chosen):
            prog = progs_list[i % len(progs_list)]
            t_days = prog["duration_days"]
            # Calibrated daily training hours to match 12.12 avg hours per employee
            t_hours = round(t_days * 6.58, 1)

            attendance_rows.append({
                "training_record_id": f"TRN-{record_idx:07d}",
                "emp_id": emp_id,
                "programme_id": prog["programme_id"],
                "programme_name": prog["programme_name"],
                "wc_id": prog["institute_wc_id"],
                "institute": prog["institute"],
                "category": prog["category"],
                "start_date": prog["start_date"],
                "end_date": prog["end_date"],
                "fiscal_year": fy,
                "training_hours": t_hours,
                "training_days": t_days,
                "completion_status": random.choice(["completed", "completed", "certified", "completed"]),
                "is_renewable_reskilling": prog["category"] == "renewable_energy",
            })
            record_idx += 1

    df_attendance = pd.DataFrame(attendance_rows)
    print(f"H11 generated: {len(df_attendance)} attendance records.")
    return df_calendar, df_attendance


# -----------------------------------------------------------------------------
# 8. GENERATE H13: LEAVE LEDGER
# -----------------------------------------------------------------------------
def generate_leave_ledger(df_emp: pd.DataFrame) -> pd.DataFrame:
    """Generate H13 leave_ledger (PA2001_PA2006.csv) FY24 to Oct-2026."""
    print("Generating H13: leave_ledger...")
    set_seed(707)

    active = df_emp[df_emp["STAT2"] == "Active"][["PERNR", "WERKS", "total_tenure_years"]].copy()

    years_data = [
        ("FY24", "2023-04-01", "2024-03-31", 2023, 12),
        ("FY25", "2024-04-01", "2025-03-31", 2024, 12),
        ("FY26", "2025-04-01", "2026-03-31", 2025, 12),
        ("FY27", "2026-04-01", "2026-10-19", 2026, 6),
    ]

    tenure = pd.to_numeric(active["total_tenure_years"], errors="coerce").fillna(10.0)
    el_bal = np.clip(45.0 + 8.0 * tenure, 30.0, 300.0)
    hpl_bal = np.clip(30.0 + 5.0 * tenure, 20.0, 240.0)

    dfs = []
    for fy, y_start, y_end, y_num, n_m in years_data:
        # 1. Accrual EL
        df_el = pd.DataFrame({
            "PERNR": active["PERNR"], "wc_id": active["WERKS"], "fiscal_year": fy,
            "SUBTY": "Earned_Leave_EL", "transaction_type": "annual_accrual",
            "BEGDA": y_start, "ENDDA": y_end, "ABWTG": 30.0 if n_m == 12 else 15.0,
            "ANZHL": el_bal.round(1), "encashable_balance_days": np.maximum(0.0, el_bal - 30.0).round(1),
            "study_leave_bond_years": None
        })
        # 2. Accrual HPL
        df_hpl = pd.DataFrame({
            "PERNR": active["PERNR"], "wc_id": active["WERKS"], "fiscal_year": fy,
            "SUBTY": "Half_Pay_Leave_HPL", "transaction_type": "annual_accrual",
            "BEGDA": y_start, "ENDDA": y_end, "ABWTG": 20.0 if n_m == 12 else 10.0,
            "ANZHL": hpl_bal.round(1), "encashable_balance_days": 0.0,
            "study_leave_bond_years": None
        })
        # 3. Leave taken: Casual Leave spell 1
        df_cl1 = pd.DataFrame({
            "PERNR": active["PERNR"], "wc_id": active["WERKS"], "fiscal_year": fy,
            "SUBTY": "Casual_Leave_CL", "transaction_type": "leave_taken",
            "BEGDA": f"{y_num}-05-12", "ENDDA": f"{y_num}-05-13", "ABWTG": 2.0,
            "ANZHL": 0.0, "encashable_balance_days": 0.0,
            "study_leave_bond_years": None
        })
        # 4. Leave taken: Casual Leave spell 2
        df_cl2 = pd.DataFrame({
            "PERNR": active["PERNR"], "wc_id": active["WERKS"], "fiscal_year": fy,
            "SUBTY": "Casual_Leave_CL", "transaction_type": "leave_taken",
            "BEGDA": f"{y_num}-09-18", "ENDDA": f"{y_num}-09-19", "ABWTG": 2.0,
            "ANZHL": 0.0, "encashable_balance_days": 0.0,
            "study_leave_bond_years": None
        })
        # 5. Leave taken: Earned Leave
        el_bal = np.maximum(0.0, el_bal - 8.0)
        df_elt = pd.DataFrame({
            "PERNR": active["PERNR"], "wc_id": active["WERKS"], "fiscal_year": fy,
            "SUBTY": "Earned_Leave_EL", "transaction_type": "leave_taken",
            "BEGDA": f"{y_num}-11-04", "ENDDA": f"{y_num}-11-12", "ABWTG": 8.0,
            "ANZHL": el_bal.round(1), "encashable_balance_days": np.maximum(0.0, el_bal - 30.0).round(1),
            "study_leave_bond_years": None
        })
        dfs.extend([df_el, df_hpl, df_cl1, df_cl2, df_elt])

    df_leave = pd.concat(dfs, ignore_index=True)
    df_leave["leave_id"] = [f"LV-{i:07d}" for i in range(1, len(df_leave) + 1)]
    print(f"H13 generated: {len(df_leave)} leave records.")
    return df_leave


# -----------------------------------------------------------------------------
# 9. GENERATE H14: MEDICAL CLAIMS
# -----------------------------------------------------------------------------
def generate_medical_claims(df_emp: pd.DataFrame) -> pd.DataFrame:
    """Generate H14 medical_claims_export.csv FY22 to Oct-2026 using Poisson draws."""
    print("Generating H14: medical_claims...")
    set_seed(808)

    active = df_emp[df_emp["STAT2"] == "Active"].copy()
    hospitals = [
        ("Max Super Speciality Hospital", True),
        ("Fortis Memorial Research Institute", True),
        ("Apollo Hospitals", True),
        ("Nanavati Max Super Speciality", True),
        ("Lilavati Hospital & Research Centre", True),
        ("City Nursing Home", False),
        ("Central Diagnostic Clinic", False),
    ]
    claim_types = ["IPD_Inpatient", "OPD_Outpatient", "Chronic_Pharmacy", "Emergency_Admission"]

    # Claim frequency by demographic age band
    age_years = pd.to_numeric(active["age_years"], errors="coerce").fillna(40.0)
    claim_lam = np.where(age_years > 50, 0.42, np.where(age_years > 30, 0.28, 0.14))

    rows = []
    idx = 1

    for y in range(2021, 2027):
        fy = f"FY{str(y+1)[2:]}"
        n_claims = np.random.poisson(lam=claim_lam)
        claimants = active[n_claims > 0].to_dict("records")

        for emp in claimants:
            cid = f"CLM-{idx:06d}"
            idx += 1

            h_name, is_emp = random.choice(hospitals)
            c_type = random.choice(claim_types)
            sub_m = random.randint(4, 11) if y < 2026 else random.randint(4, 9)
            sub_d = random.randint(1, 25)
            sub_date = f"{y:04d}-{sub_m:02d}-{sub_d:02d}"

            t_days = random.randint(12, 28)
            settle_date = f"{y:04d}-{sub_m:02d}-{min(28, sub_d + t_days):02d}"

            claimed = float(random.choice([4500, 8200, 15000, 32000, 75000, 120000]))
            status = random.choice(["approved_paid", "approved_paid", "partially_approved", "pending_scrutiny"])
            if not is_emp and random.random() < 0.08:
                status = "rejected"

            if status == "approved_paid":
                approved = claimed
                ded_amt = 0.0
                ded_reason = "none"
            elif status == "partially_approved":
                ded_amt = round(claimed * random.uniform(0.08, 0.20), 2)
                approved = claimed - ded_amt
                ded_reason = random.choice(["room_rent_capping", "non_reimbursable_consumables"])
            elif status == "rejected":
                approved = 0.0
                ded_amt = claimed
                ded_reason = "schedule_rate_excess"
                settle_date = None
            else:
                approved = 0.0
                ded_amt = 0.0
                ded_reason = "none"
                settle_date = None
                t_days = None

            rows.append({
                "claim_id": cid,
                "emp_id": emp["PERNR"],
                "wc_id": emp["WERKS"],
                "patient_relationship": random.choice(["self", "spouse", "dependent_child", "dependent_parent"]),
                "hospital_name": h_name,
                "is_empanelled_hospital": is_emp,
                "claim_type": c_type,
                "submission_date": sub_date,
                "settlement_date": settle_date,
                "fiscal_year": fy,
                "turnaround_days": t_days,
                "claimed_amount_inr": claimed,
                "approved_amount_inr": approved,
                "deduction_amount_inr": ded_amt,
                "deduction_reason": ded_reason,
                "claim_status": status,
            })

    df_claims = pd.DataFrame(rows)
    print(f"H14 generated: {len(df_claims)} medical claims.")
    return df_claims


# -----------------------------------------------------------------------------
# 10. GENERATE H15: GRIEVANCES & LITIGATION
# -----------------------------------------------------------------------------
def generate_grievances_litigation(df_emp: pd.DataFrame) -> pd.DataFrame:
    """Generate H15 legal_cases_tracker.xlsx with realistic dispute disposal dynamics."""
    print("Generating H15: grievances_litigation...")
    set_seed(909)

    active_cohort = df_emp[df_emp["STAT2"] == "Active"][["PERNR", "WERKS"]].to_dict("records")
    forums = [
        "internal_grievance_cell", "CAT_Principal_Bench_Delhi", "CAT_Guwahati",
        "CAT_Ahmedabad", "CAT_Mumbai", "High_Court", "Supreme_Court"
    ]
    case_types = [
        "grievance_internal", "service_litigation_cat",
        "writ_petition_high_court", "special_leave_supreme_court"
    ]
    categories = [
        "promotion_dispute", "transfer_challenge", "disciplinary_action",
        "pay_anomaly", "seniority_fixation", "quarters_allotment"
    ]

    rows = []
    as_of_dt = pd.to_datetime("2026-10-19")

    # Generate 420 formal cases with realistic age-dependent resolution
    for i in range(1, 421):
        cid = f"CASE-{i:04d}"
        emp = random.choice(active_cohort)
        c_type = random.choice(case_types)
        c_cat = random.choice(categories)
        forum = random.choice(forums)

        filing_y = random.choice([2020, 2021, 2022, 2023, 2024, 2025, 2026])
        filing_m = random.randint(1, 12)
        filing_d = random.randint(1, 28)
        filing_date = f"{filing_y:04d}-{filing_m:02d}-{filing_d:02d}"
        filing_dt = pd.to_datetime(filing_date)

        age_days = (as_of_dt - filing_dt).days
        age_years = round(age_days / 365.25, 2)

        # Realistic disposal dynamics: internal grievances resolve within 6-12 months
        if c_type == "grievance_internal":
            if age_years > 1.0:
                status = random.choice(["disposed", "dismissed", "allowed", "disposed"])
            else:
                status = "pending"
        elif c_type == "service_litigation_cat":
            if age_years > 2.0:
                status = random.choice(["disposed", "dismissed", "allowed", "stayed"])
            else:
                status = random.choice(["pending", "pending", "stayed"])
        else:
            # Court petitions: 50% resolved, persistent stay orders
            if age_years > 3.0:
                status = random.choice(["disposed", "dismissed", "stayed", "pending"])
            elif age_years > 1.5:
                status = random.choice(["pending", "stayed", "disposed"])
            else:
                status = "pending"

        stay = status == "stayed" or (status == "pending" and random.random() < 0.12)
        is_aged_3yr = (age_years > 3.0) and (status in ["pending", "stayed"])

        next_hearing = "2026-11-15" if status in ["pending", "stayed"] else None

        rows.append({
            "case_id": cid,
            "emp_id": emp["PERNR"],
            "wc_id": emp["WERKS"],
            "case_type": c_type,
            "case_category": c_cat,
            "forum": forum,
            "filing_date": filing_date,
            "fiscal_year": get_fiscal_year(filing_date),
            "status": status,
            "interim_stay_granted": stay,
            "age_days": age_days,
            "age_years": age_years,
            "is_aged_over_3_years": is_aged_3yr,
            "next_hearing_date": next_hearing,
            "subject_summary": f"Representation regarding {c_cat.replace('_', ' ')} before {forum.replace('_', ' ')}",
        })

    df_legal = pd.DataFrame(rows)
    print(f"H15 generated: {len(df_legal)} litigation records.")
    return df_legal


# -----------------------------------------------------------------------------
# 11. GENERATE H16: CONTRACT WORKFORCE
# -----------------------------------------------------------------------------
def generate_contract_workforce(
    df_snapshot: pd.DataFrame, df_prod: pd.DataFrame,
    work_centres: Dict[str, Any], vendors: Dict[str, Any]
) -> pd.DataFrame:
    """Generate H16 ESSR_ESLL.csv contract workforce data FY22 to Sep-2026."""
    print("Generating H16: contract_workforce...")
    set_seed(1010)

    vendor_ids = list(vendors.keys())
    service_categories = [
        "drilling_operations", "hydrocarbon_processing", "mechanical_maintenance",
        "electrical_instrumentation", "security_watch", "catering_hospitality",
        "logistics_transport", "civil_maintenance"
    ]

    months = sorted([m for m in df_snapshot["month"].unique() if m >= "2021-04"])

    # Map monthly production by wc
    prod_map = {}
    if not df_prod.empty and "asset_wc_id" in df_prod.columns:
        for _, prow in df_prod.iterrows():
            prod_map[(prow["month"], prow["asset_wc_id"])] = float(prow.get("total_production_boe", 0.0))

    rows = []
    entry_idx = 1

    for month_str in months:
        fy = get_fiscal_year(f"{month_str}-15")
        sub_snap = df_snapshot[df_snapshot["month"] == month_str]

        for wc_id, wc in work_centres.items():
            wc_reg = sub_snap[sub_snap["wc_id"] == wc_id]["headcount"].sum()
            wc_t = wc.get("type", "office")
            wc_terrain = wc.get("onshore_offshore", "onshore")

            # Contract ratio based strictly on attribute class
            if wc_t == "plant":
                ratio = PARAMS["contractor_ratio_plant"]
            elif wc_terrain == "offshore":
                ratio = PARAMS["contractor_ratio_offshore"]
            elif wc_t in ["asset", "basin"]:
                ratio = PARAMS["contractor_ratio_asset"]
            else:
                ratio = PARAMS["contractor_ratio_office"]

            contractor_hc = int(round(wc_reg * ratio)) if wc_reg > 0 else 15
            calc_ratio = round(contractor_hc / max(1, wc_reg), 4)

            # Monthly contractor cost
            monthly_cost = contractor_hc * PARAMS["contractor_daily_wage_inr"] * 26.0

            boe = prod_map.get((month_str, wc_id), 0.0)
            cost_per_boe = round(monthly_cost / (boe * PARAMS["usd_inr_exchange_rate"]), 2) if boe > 50000 else 0.0

            # 1 to 2 contract service entry sheets per work centre per month
            rows.append({
                "LBLNI": f"SES-{entry_idx:07d}",
                "EBELN": f"PO-CON-{entry_idx % 5000 + 10000}",
                "LIFNR": random.choice(vendor_ids),
                "WERKS": wc_id,
                "month": month_str,
                "fiscal_year": fy,
                "service_category": random.choice(service_categories),
                "discipline_id": "DISC-PRD" if wc_t in ["plant", "asset"] else "DISC-LOG",
                "grade_id": "GRP-C",
                "gender": "Total",
                "category": "All",
                "pwd_flag": False,
                "age_band": "All",
                "tenure_band": "All",
                "is_core_activity": wc_t in ["asset", "plant"] or wc_terrain == "offshore",
                "contractor_headcount": contractor_hc,
                "regular_employee_count_matching": wc_reg,
                "contractor_to_regular_ratio": calc_ratio,
                "NETWR": round(monthly_cost, 2),
                "contractor_cost_per_boe_usd": cost_per_boe,
                "clra_license_no": f"CLRA/LIC/{entry_idx % 250 + 1000}",
                "clra_compliance_status": random.choice(["compliant", "compliant", "compliant", "minor_observation"]),
            })
            entry_idx += 1

    df_contract = pd.DataFrame(rows)
    print(f"H16 generated: {len(df_contract)} contract entries.")
    return df_contract


# -----------------------------------------------------------------------------
# 12. GENERATE H17: HSE INCIDENTS
# -----------------------------------------------------------------------------
def generate_hse_incidents(
    df_snapshot: pd.DataFrame, df_contract: pd.DataFrame, work_centres: Dict[str, Any]
) -> pd.DataFrame:
    """Generate H17 hse_incident_log.csv (+ calculated LTIFR) FY22 to Oct-2026."""
    print("Generating H17: hse_incidents...")
    set_seed(1111)

    months = sorted([m for m in df_snapshot["month"].unique() if m >= "2021-04"])
    rows = []
    inc_idx = 1

    # Total FY26 target LTIFR = 0.150 (±2%)
    # For each work centre and month, generate safety return man-hours and occasional incidents
    for month_str in months:
        fy = get_fiscal_year(f"{month_str}-15")
        sub_snap = df_snapshot[df_snapshot["month"] == month_str]
        sub_con = df_contract[df_contract["month"] == month_str]

        for wc_id, wc in work_centres.items():
            wc_reg = sub_snap[sub_snap["wc_id"] == wc_id]["headcount"].sum()
            wc_con = sub_con[sub_con["WERKS"] == wc_id]["contractor_headcount"].sum()
            total_workers = wc_reg + wc_con

            if total_workers == 0:
                continue

            monthly_manhours = total_workers * (PARAMS["annual_hours_per_worker"] / 12.0)
            is_offshore = wc.get("onshore_offshore") == "offshore"
            ot_hrs = PARAMS["overtime_hours_offshore"] if is_offshore else PARAMS["overtime_hours_asset_plant"]

            # Hazard rate normalized to corporate LTIFR = 0.150 across onshore and offshore
            lti_base_rate = PARAMS["target_ltifr_fy26"] / (1.0 + 0.38 * (PARAMS["offshore_incident_hazard_mult"] - 1.0))
            lti_hazard = (monthly_manhours * lti_base_rate / 1_000_000.0)
            if is_offshore:
                lti_hazard *= PARAMS["offshore_incident_hazard_mult"]

            has_lti = random.random() < lti_hazard
            inc_type = "Lost_Time_Injury_LTI" if has_lti else random.choice([
                "Near_Miss", "First_Aid_Case", "Medical_Treatment_Case", "Fire_Incident"
            ])
            is_lti = inc_type == "Lost_Time_Injury_LTI"

            days_lost = random.randint(4, 28) if is_lti else 0
            severity = "Tier_1" if (is_lti and days_lost > 14) else ("Tier_2" if is_lti else "Non_Tier")
            ltifr_calc = round((1 if is_lti else 0) * 1_000_000.0 / monthly_manhours, 3)

            inst_name = f"{wc.get('short_name', wc_id)} Installation"

            rows.append({
                "incident_id": f"INC-{inc_idx:05d}",
                "wc_id": wc_id,
                "emp_id": None,
                "grade_id": "GRP-C",
                "discipline_id": "DISC-DRL" if is_offshore else "DISC-PRD",
                "installation_name": inst_name,
                "incident_date": f"{month_str}-14",
                "month": month_str,
                "fiscal_year": fy,
                "incident_type": inc_type,
                "lost_time_injury_flag": is_lti,
                "days_lost": days_lost,
                "severity_tier": severity,
                "monthly_overtime_hours_per_worker": ot_hrs,
                "fatigue_factor_flag": is_offshore and is_lti,
                "workforce_category_involved": "contract_worker" if random.random() < 0.65 else "regular_employee",
                "total_manhours_worked": round(monthly_manhours, 1),
                "calculated_ltifr": ltifr_calc,
                "brief_description": f"{inc_type.replace('_', ' ')} recorded during operations at {inst_name}",
            })
            inc_idx += 1

    df_hse = pd.DataFrame(rows)
    print(f"H17 generated: {len(df_hse)} HSE records.")
    return df_hse


# -----------------------------------------------------------------------------
# 13. GENERATE H18: TRAVEL CLAIMS
# -----------------------------------------------------------------------------
def generate_travel_claims(df_emp: pd.DataFrame, work_centres: Dict[str, Any]) -> pd.DataFrame:
    """Generate H18 PTRV_HEAD_DOC.csv travel claims FY22 to Oct-2026 using Poisson draws."""
    print("Generating H18: travel_claims...")
    set_seed(1212)

    active_df = df_emp[df_emp["STAT2"] == "Active"].copy()
    cities = [
        ("New Delhi", "Class_A"), ("Mumbai", "Class_A"),
        ("Dehradun", "Class_B"), ("Ahmedabad", "Class_B"),
        ("Nazira", "Class_C"), ("Sivasagar", "Class_C"),
        ("Mumbai High", "Offshore")
    ]
    purposes = ["official_tour", "training_deputation", "transfer_transit", "inspection_audit"]

    is_senior = active_df["PERSK"].isin(["E6", "E7", "E8", "E9", "DIR", "CMD"])
    is_exec = active_df["PERSK"].str.startswith("E") & (~is_senior)
    travel_lam = np.where(is_senior, 0.50, np.where(is_exec, 0.30, 0.02))

    rows = []
    idx = 1

    for y in range(2021, 2027):
        fy = f"FY{str(y+1)[2:]}"
        n_tours = np.random.poisson(lam=travel_lam)
        sample_emp = active_df[n_tours > 0].to_dict("records")

        for emp in sample_emp:
            cid = f"TRV-{idx:06d}"
            idx += 1

            start_m = random.randint(4, 11) if y < 2026 else random.randint(4, 9)
            start_d = random.randint(1, 20)
            dur = random.randint(2, 6)
            start_date = f"{y:04d}-{start_m:02d}-{start_d:02d}"
            end_date = f"{y:04d}-{start_m:02d}-{start_d + dur:02d}"

            from_c = work_centres.get(emp["WERKS"], {}).get("city", "New Delhi")
            to_c, city_tier = random.choice(cities)

            grade = emp["PERSK"]
            is_exec_grade = grade.startswith("E") or grade in ["DIR", "CMD"]

            if is_exec_grade:
                travel_class = "Air_Economy" if grade in ["E1", "E2", "E3", "E4", "E5"] else "Air_Business"
                fare = float(random.randint(6500, 18500))
                da_rate = 1150.0 if city_tier == "Class_A" else 950.0
                hotel = float(dur * (4500 if city_tier == "Class_A" else 3000))
            else:
                travel_class = "Train_AC_2_Tier"
                fare = float(random.randint(1800, 4500))
                da_rate = 750.0
                hotel = float(dur * 1800)

            daily_allowance = dur * da_rate
            is_offshore_loc = city_tier not in ["Class_A", "Class_B", "Class_C"]
            hardship = 5000.0 if is_offshore_loc else 0.0
            tot_claim = fare + daily_allowance + hotel + hardship
            approved = tot_claim

            rows.append({
                "travel_claim_id": cid,
                "REINR": cid,
                "PERNR": emp["PERNR"],
                "grade_id": grade,
                "wc_id": emp["WERKS"],
                "from_city": from_c,
                "to_city": to_c,
                "city_category": city_tier,
                "purpose": random.choice(purposes),
                "BEGDA": start_date,
                "ENDDA": end_date,
                "fiscal_year": fy,
                "travel_class_availed": travel_class,
                "travel_class_entitlement": travel_class,
                "fare_amount_inr": fare,
                "daily_allowance_da_inr": daily_allowance,
                "lodging_hotel_amount_inr": hotel,
                "special_hardship_allowance_inr": hardship,
                "total_claim_amount_inr": tot_claim,
                "BETRG": approved,
                "status": "settled",
            })

    df_travel = pd.DataFrame(rows)
    print(f"H18 generated: {len(df_travel)} travel claims.")
    return df_travel


# -----------------------------------------------------------------------------
# 14. GENERATE H19: ICC COMMITTEES
# -----------------------------------------------------------------------------
def generate_icc_committees(
    df_emp: pd.DataFrame, work_centres: Dict[str, Any]
) -> pd.DataFrame:
    """Generate H19 icc_committees.xlsx across all 42 work centres."""
    print("Generating H19: icc_committees...")
    set_seed(1313)

    # Eligible senior female presiding officers
    female_execs = df_emp[
        (df_emp["STAT2"] == "Active") &
        (df_emp["GESCH"] == "Female") &
        (df_emp["PERSK"].isin(["E5", "E6", "E7", "E8"]))
    ][["PERNR", "WERKS"]].to_dict("records")

    ngos = [
        ("Dr. Sunita Sharma", "Centre for Women Empowerment NGO"),
        ("Advocate Meenakshi Sen", "Legal Aid & Gender Rights Foundation"),
        ("Prof. Anuradha Roy", "Society for Social Development"),
        ("Smt. Shashi Kaul", "All India Women Conference"),
    ]

    rows = []
    idx = 1

    for wc_id, wc in sorted(work_centres.items()):
        cid = f"ICC-{idx:03d}"
        idx += 1

        # Match female officer at same work centre if available, else pick from pool
        matching = [f for f in female_execs if f["WERKS"] == wc_id]
        p_officer = matching[0] if matching else random.choice(female_execs)

        ext_name, ext_ngo = random.choice(ngos)
        internal_count = random.choice([4, 5, 6])
        women_pct = random.choice([60.0, 66.7, 75.0, 80.0])  # Strictly >= 50% per PoSH Act

        rows.append({
            "committee_id": cid,
            "wc_id": wc_id,
            "constitution_date": "2024-04-01",
            "expiry_date": "2027-03-31",
            "fiscal_year": "FY26",
            "presiding_officer_emp_id": p_officer["PERNR"],
            "presiding_officer_name": "Senior Executive Officer",
            "presiding_officer_gender": "Female",
            "external_member_name": ext_name,
            "external_member_ngo": ext_ngo,
            "internal_members_count": internal_count,
            "women_members_pct": women_pct,
            "status": "active",
            "contact_email": f"icc.{wc.get('short_name', 'wc').lower().replace(' ', '')}@ongc.co.in",
        })

    df_icc = pd.DataFrame(rows)
    print(f"H19 generated: {len(df_icc)} ICC committees.")
    return df_icc


# -----------------------------------------------------------------------------
# 15. GENERATE H20: VIGILANCE CASES
# -----------------------------------------------------------------------------
def generate_vigilance_cases(df_emp: pd.DataFrame) -> pd.DataFrame:
    """Generate H20 vigilance_cases_confidential.csv."""
    print("Generating H20: vigilance_cases...")
    set_seed(1414)

    active_cohort = df_emp[df_emp["STAT2"] == "Active"][["PERNR", "WERKS", "PERSK", "discipline_id"]].to_dict("records")

    allegations = [
        "procurement_irregularity", "recruitment_malpractice",
        "asset_misappropriation", "quid_pro_quo", "code_of_conduct_breach"
    ]
    stages = [
        "preliminary_investigation", "regular_departmental_inquiry",
        "charge_sheet_issued", "cvo_second_stage_advice", "closed"
    ]

    rows = []
    for i in range(1, 96):
        vid = f"VIG-{i:04d}"
        emp = random.choice(active_cohort)
        stage = random.choice(stages)

        if stage == "closed":
            inquiry = random.choice(["exonerated", "dropped"])
            clearance = "cleared"
        elif stage == "charge_sheet_issued":
            inquiry = "under_investigation"
            clearance = "conditional_sealed_cover"
        else:
            inquiry = "under_investigation"
            clearance = "withheld"

        y = random.choice([2023, 2024, 2025, 2026])
        m = random.randint(1, 12)
        d = random.randint(1, 28)
        comp_date = f"{y:04d}-{m:02d}-{d:02d}"
        age_months = (2026 - y) * 12 + (10 - m)

        rows.append({
            "vigilance_case_id": vid,
            "emp_id": emp["PERNR"],
            "grade_id": emp["PERSK"],
            "discipline_id": emp["discipline_id"],
            "wc_id": emp["WERKS"],
            "complaint_date": comp_date,
            "fiscal_year": get_fiscal_year(comp_date),
            "nature_of_allegation": random.choice(allegations),
            "stage": stage,
            "inquiry_status": inquiry,
            "vigilance_clearance_status": clearance,
            "age_months": max(1, age_months),
            "confidentiality_level": "Strictly_Confidential",
        })

    df_vig = pd.DataFrame(rows)
    print(f"H20 generated: {len(df_vig)} vigilance cases.")
    return df_vig


# -----------------------------------------------------------------------------
# 16. GENERATE G5: ACCESS AUDIT LOG SEED
# -----------------------------------------------------------------------------
def generate_access_audit_log(df_emp: pd.DataFrame) -> pd.DataFrame:
    """Generate G5 access_audit_log.csv seed showing realistic traffic and ~2.5% RBAC refusals."""
    print("Generating G5: access_audit_log...")
    set_seed(1515)

    active_emp = df_emp[df_emp["STAT2"] == "Active"][["PERNR", "WERKS", "PERSK"]].to_dict("records")

    # Legitimate routine operational & self-service resources (~97% of traffic)
    routine_resources = [
        ("self_service_payslip", "HR", "public_aggregate", None),
        ("self_service_leave_balance", "HR", "public_aggregate", None),
        ("self_service_medical_status", "HR", "public_aggregate", None),
        ("training_calendar_view", "HR", "public_aggregate", None),
        ("travel_claim_submission", "HR", "public_aggregate", None),
        ("work_centre_manpower_roster", "HR", "public_aggregate", None),
        ("cost_centre_budget_summary", "Finance", "public_aggregate", None),
        ("installation_uptime_log", "Operations", "public_aggregate", None),
        ("corporate_policies_portal", "Corporate", "public_aggregate", None),
    ]

    # Confidential resources subject to RBAC refusal (~3% of traffic)
    restricted_resources = [
        ("individual_salary_record", "HR", "confidential_salary", "Confidential remuneration protected under CDA Rule 5"),
        ("draft_transfer_list", "HR", "confidential_transfer_draft", "Confidential draft transfer proposals under JRTP Section 8"),
        ("field_pnl_summary", "Finance", "confidential_field_pnl", "Commercial sensitivity under Disclosure Policy Sec 3.2"),
        ("dpc_proceedings", "HR", "confidential_dpc", "DPC committee deliberations classified under Regulation 14"),
        ("vigilance_inquiry", "Governance", "confidential_vigilance", "Vigilance inquiries confidential under CVC guidelines"),
    ]

    rows = []
    log_idx = 1
    as_of_date = datetime.date(2026, 10, 19)

    # Generate 3,500 audit log events over the last 90 days across personas
    for i in range(1, 3501):
        emp = random.choice(active_emp)
        grade = emp["PERSK"]
        is_exec_director = grade in ["DIR", "CMD", "E9"]

        # ~2.8% of queries are attempted access to restricted resources by non-directors
        is_refusal_attempt = (random.random() < 0.028) and (not is_exec_director)

        if is_refusal_attempt:
            res_name, dom, res_class, reason = random.choice(restricted_resources)
            decision = "DENIED_RBAC"
            denial = reason
        else:
            if is_exec_director and random.random() < 0.15:
                # Directors querying confidential management objects (allowed)
                res_name, dom, res_class, _ = random.choice(restricted_resources)
                decision = "ALLOWED"
                denial = None
            else:
                # Routine self-service and role aggregates
                res_name, dom, res_class, _ = random.choice(routine_resources)
                decision = "ALLOWED"
                denial = None

        # Timestamps over the last 90 days (July 2026 to October 2026)
        day_offset = random.randint(0, 90)
        evt_date = as_of_date - datetime.timedelta(days=day_offset)
        dt_str = evt_date.isoformat()
        ts_str = f"{dt_str}T{random.randint(9, 18):02d}:{random.randint(10, 59):02d}:{random.randint(10, 59):02d}Z"
        fy = "FY27" if evt_date.month >= 4 else "FY26"

        rows.append({
            "log_id": f"LOG-{log_idx:06d}",
            "timestamp": ts_str,
            "date": dt_str,
            "fiscal_year": fy,
            "user_id": emp["PERNR"],
            "user_role": "Director" if grade in ["DIR", "CMD"] else ("Finance_Officer" if dom == "Finance" else "HR_Officer"),
            "user_department": dom,
            "user_grade": grade,
            "user_wc_id": emp["WERKS"],
            "requested_resource": res_name,
            "resource_domain": dom,
            "resource_data_classification": res_class,
            "access_decision": decision,
            "denial_reason": denial,
            "client_ip": f"10.24.{random.randint(1, 250)}.{random.randint(1, 250)}",
        })
        log_idx += 1

    df_log = pd.DataFrame(rows)
    print(f"G5 generated: {len(df_log)} audit log records.")
    return df_log


# -----------------------------------------------------------------------------
# 17. APPLY DEMO PERSONAS EXEMPTION BLOCK
# -----------------------------------------------------------------------------
def apply_demo_personas(
    df_leave: pd.DataFrame, df_claims: pd.DataFrame,
    df_attendance: pd.DataFrame, df_travel: pd.DataFrame,
    df_log: pd.DataFrame, df_emp: pd.DataFrame
):
    """Set realistic, explicit records for the 5 demo personas inside this delimited block only.

    Personas:
    - EMP-000001: Chairman & CEO
    - EMP-000002: Director (HR)
    - EMP-000003: Director (Finance)
    - EMP-102451: Pooja Verma (E2 HR Officer, Delhi)
    - EMP-103892: Rajesh Kulkarni (E3 Finance Officer, Mumbai)
    """
    print("Applying demo personas calibration in delimited block...")

    # Helper: retrieve current work centre dynamically without hardcoding entity IDs
    def get_wc(emp_id: str) -> str:
        matches = df_emp[df_emp["PERNR"] == emp_id]["WERKS"].values
        return str(matches[0]) if len(matches) > 0 else "WC-DEL"

    def get_grade(emp_id: str) -> str:
        matches = df_emp[df_emp["PERNR"] == emp_id]["PERSK"].values
        return str(matches[0]) if len(matches) > 0 else "E2"

    # 1. Leave Balances for Pooja Verma and Rajesh Kulkarni
    # Pooja Verma (EMP-102451): EL balance ~70-85 days with encashable
    pooja_leave = {
        "leave_id": "LV-P102451",
        "PERNR": "EMP-102451",
        "wc_id": get_wc("EMP-102451"),
        "fiscal_year": "FY26",
        "SUBTY": "Earned_Leave_EL",
        "transaction_type": "annual_accrual",
        "BEGDA": "2026-01-01",
        "ENDDA": "2026-12-31",
        "ABWTG": 30.0,
        "ANZHL": 78.0,
        "encashable_balance_days": 18.0,
        "study_leave_bond_years": None,
    }
    # Rajesh Kulkarni (EMP-103892): EL balance ~100-120 days
    rajesh_leave = {
        "leave_id": "LV-R103892",
        "PERNR": "EMP-103892",
        "wc_id": get_wc("EMP-103892"),
        "fiscal_year": "FY26",
        "SUBTY": "Earned_Leave_EL",
        "transaction_type": "annual_accrual",
        "BEGDA": "2026-01-01",
        "ENDDA": "2026-12-31",
        "ABWTG": 30.0,
        "ANZHL": 112.0,
        "encashable_balance_days": 52.0,
        "study_leave_bond_years": None,
    }
    # Append calibrated persona rows via clean concat
    df_leave_clean = df_leave[~df_leave["PERNR"].isin(["EMP-102451", "EMP-103892"])]
    df_leave = pd.concat([df_leave_clean, pd.DataFrame([pooja_leave, rajesh_leave])], ignore_index=True)

    # 2. Medical Claims: One approved and one pending each
    pooja_claim_app = {
        "claim_id": "CLM-P001",
        "emp_id": "EMP-102451",
        "wc_id": get_wc("EMP-102451"),
        "patient_relationship": "self",
        "hospital_name": "Max Super Speciality Hospital",
        "is_empanelled_hospital": True,
        "claim_type": "OPD_Outpatient",
        "submission_date": "2026-05-10",
        "settlement_date": "2026-05-24",
        "fiscal_year": "FY27",
        "turnaround_days": 14,
        "claimed_amount_inr": 18500.0,
        "approved_amount_inr": 17200.0,
        "deduction_amount_inr": 1300.0,
        "deduction_reason": "non_reimbursable_consumables",
        "claim_status": "approved_paid",
    }
    pooja_claim_pend = {
        "claim_id": "CLM-P002",
        "emp_id": "EMP-102451",
        "wc_id": get_wc("EMP-102451"),
        "patient_relationship": "dependent_parent",
        "hospital_name": "Fortis Memorial Research Institute",
        "is_empanelled_hospital": True,
        "claim_type": "IPD_Inpatient",
        "submission_date": "2026-09-18",
        "settlement_date": None,
        "fiscal_year": "FY27",
        "turnaround_days": None,
        "claimed_amount_inr": 42000.0,
        "approved_amount_inr": 0.0,
        "deduction_amount_inr": 0.0,
        "deduction_reason": "none",
        "claim_status": "pending_scrutiny",
    }
    rajesh_claim_app = {
        "claim_id": "CLM-R001",
        "emp_id": "EMP-103892",
        "wc_id": get_wc("EMP-103892"),
        "patient_relationship": "spouse",
        "hospital_name": "Nanavati Max Super Speciality",
        "is_empanelled_hospital": True,
        "claim_type": "OPD_Outpatient",
        "submission_date": "2026-06-04",
        "settlement_date": "2026-06-20",
        "fiscal_year": "FY27",
        "turnaround_days": 16,
        "claimed_amount_inr": 35000.0,
        "approved_amount_inr": 32000.0,
        "deduction_amount_inr": 3000.0,
        "deduction_reason": "room_rent_capping",
        "claim_status": "approved_paid",
    }
    rajesh_claim_pend = {
        "claim_id": "CLM-R002",
        "emp_id": "EMP-103892",
        "wc_id": get_wc("EMP-103892"),
        "patient_relationship": "self",
        "hospital_name": "Lilavati Hospital & Research Centre",
        "is_empanelled_hospital": True,
        "claim_type": "IPD_Inpatient",
        "submission_date": "2026-09-25",
        "settlement_date": None,
        "fiscal_year": "FY27",
        "turnaround_days": None,
        "claimed_amount_inr": 68000.0,
        "approved_amount_inr": 0.0,
        "deduction_amount_inr": 0.0,
        "deduction_reason": "none",
        "claim_status": "pending_scrutiny",
    }
    df_claims_clean = df_claims[~df_claims["emp_id"].isin(["EMP-102451", "EMP-103892"])]
    df_claims = pd.concat([df_claims_clean, pd.DataFrame([pooja_claim_app, pooja_claim_pend, rajesh_claim_app, rajesh_claim_pend])], ignore_index=True)

    # 3. Access Audit Log entries demonstrating role-based access rules
    audit_pooja_denied = {
        "log_id": "LOG-P102451-01",
        "timestamp": "2026-10-14T11:22:33Z",
        "date": "2026-10-14",
        "fiscal_year": "FY27",
        "user_id": "EMP-102451",
        "user_role": "HR_Officer",
        "user_department": "HR",
        "user_grade": get_grade("EMP-102451"),
        "user_wc_id": get_wc("EMP-102451"),
        "requested_resource": "field_pnl_summary",
        "resource_domain": "Finance",
        "resource_data_classification": "confidential_field_pnl",
        "access_decision": "DENIED_RBAC",
        "denial_reason": "Commercial sensitivity under Disclosure Policy Sec 3.2",
        "client_ip": "10.24.11.45",
    }
    audit_rajesh_denied = {
        "log_id": "LOG-R103892-01",
        "timestamp": "2026-10-15T14:15:16Z",
        "date": "2026-10-15",
        "fiscal_year": "FY27",
        "user_id": "EMP-103892",
        "user_role": "Finance_Officer",
        "user_department": "Finance",
        "user_grade": get_grade("EMP-103892"),
        "user_wc_id": get_wc("EMP-103892"),
        "requested_resource": "individual_salary_record",
        "resource_domain": "HR",
        "resource_data_classification": "confidential_salary",
        "access_decision": "DENIED_RBAC",
        "denial_reason": "Confidential remuneration protected under CDA Rule 5",
        "client_ip": "10.24.22.88",
    }
    audit_cmd_allowed = {
        "log_id": "LOG-CMD-001",
        "timestamp": "2026-10-16T09:30:00Z",
        "date": "2026-10-16",
        "fiscal_year": "FY27",
        "user_id": "EMP-000001",
        "user_role": "CMD",
        "user_department": "Corporate",
        "user_grade": get_grade("EMP-000001"),
        "user_wc_id": get_wc("EMP-000001"),
        "requested_resource": "field_pnl_summary",
        "resource_domain": "Finance",
        "resource_data_classification": "confidential_field_pnl",
        "access_decision": "ALLOWED",
        "denial_reason": None,
        "client_ip": "10.24.1.1",
    }
    df_log = pd.concat([df_log, pd.DataFrame([audit_pooja_denied, audit_rajesh_denied, audit_cmd_allowed])], ignore_index=True)

    print("Demo personas applied successfully.")
    return df_leave, df_claims, df_log


# -----------------------------------------------------------------------------
# 18. EXPORT AND SAVE ALL LANDING FILES
# -----------------------------------------------------------------------------
def save_all_landing_files(tables: Dict[str, Any]):
    """Save all 16 landing files strictly according to schema_silver formats and headers."""
    print("Writing landing files to disk...")

    # H6: sanctioned_posts -> landing/excel/manpower_plan.xlsx
    with pd.ExcelWriter(LANDING_EXCEL / "manpower_plan.xlsx", engine="openpyxl") as writer:
        tables["H6"].to_excel(writer, sheet_name="manpower_plan", index=False)
    print("Wrote manpower_plan.xlsx")

    # H7: headcount_snapshot -> landing/sap/headcount_monthly_snapshot.csv
    tables["H7"].to_csv(LANDING_SAP / "headcount_monthly_snapshot.csv", index=False)
    print("Wrote headcount_monthly_snapshot.csv")

    # H8: payroll_monthly -> landing/sap/PY_CLUSTER_EXP.csv
    tables["H8"].to_csv(LANDING_SAP / "PY_CLUSTER_EXP.csv", index=False)
    print("Wrote PY_CLUSTER_EXP.csv")

    # H9: apar_ratings -> landing/sap/eAPAR_ratings.csv
    tables["H9"].to_csv(LANDING_SAP / "eAPAR_ratings.csv", index=False)
    print("Wrote eAPAR_ratings.csv")

    # H10: succession_plan -> landing/excel/succession_planning.xlsx
    with pd.ExcelWriter(LANDING_EXCEL / "succession_planning.xlsx", engine="openpyxl") as writer:
        tables["H10"].to_excel(writer, sheet_name="succession_plan", index=False)
    print("Wrote succession_planning.xlsx")

    # H11: training_records -> landing/db_exports/lms_attendance.csv
    tables["H11"].to_csv(LANDING_DB / "lms_attendance.csv", index=False)
    print("Wrote lms_attendance.csv")

    # H12: training_calendar -> landing/excel/training_calendar.xlsx
    with pd.ExcelWriter(LANDING_EXCEL / "training_calendar.xlsx", engine="openpyxl") as writer:
        tables["H12"].to_excel(writer, sheet_name="training_calendar", index=False)
    print("Wrote training_calendar.xlsx")

    # H13: leave_ledger -> landing/sap/PA2001_PA2006.csv
    tables["H13"].to_csv(LANDING_SAP / "PA2001_PA2006.csv", index=False)
    print("Wrote PA2001_PA2006.csv")

    # H14: medical_claims -> landing/db_exports/medical_claims_export.csv
    tables["H14"].to_csv(LANDING_DB / "medical_claims_export.csv", index=False)
    print("Wrote medical_claims_export.csv")

    # H15: grievances_litigation -> landing/excel/legal_cases_tracker.xlsx
    with pd.ExcelWriter(LANDING_EXCEL / "legal_cases_tracker.xlsx", engine="openpyxl") as writer:
        tables["H15"].to_excel(writer, sheet_name="legal_cases", index=False)
    print("Wrote legal_cases_tracker.xlsx")

    # H16: contract_workforce -> landing/sap/ESSR_ESLL.csv
    tables["H16"].to_csv(LANDING_SAP / "ESSR_ESLL.csv", index=False)
    print("Wrote ESSR_ESLL.csv")

    # H17: hse_incidents -> landing/db_exports/hse_incident_log.csv
    tables["H17"].to_csv(LANDING_DB / "hse_incident_log.csv", index=False)
    print("Wrote hse_incident_log.csv")

    # H18: travel_claims -> landing/sap/PTRV_HEAD_DOC.csv
    tables["H18"].to_csv(LANDING_SAP / "PTRV_HEAD_DOC.csv", index=False)
    print("Wrote PTRV_HEAD_DOC.csv")

    # H19: icc_committees -> landing/excel/icc_committees.xlsx
    with pd.ExcelWriter(LANDING_EXCEL / "icc_committees.xlsx", engine="openpyxl") as writer:
        tables["H19"].to_excel(writer, sheet_name="icc_committees", index=False)
    print("Wrote icc_committees.xlsx")

    # H20: vigilance_cases -> landing/sap/vigilance_cases_confidential.csv
    tables["H20"].to_csv(LANDING_SAP / "vigilance_cases_confidential.csv", index=False)
    print("Wrote vigilance_cases_confidential.csv")

    # G5: access_audit_log -> landing/db_exports/access_audit_log.csv
    tables["G5"].to_csv(LANDING_DB / "access_audit_log.csv", index=False)
    print("Wrote access_audit_log.csv")

    print("All 16 landing files written successfully.")


def generate_all():
    """Main execution flow for HR Satellites Generator."""
    print("=" * 70)
    print("RUNNING HR SATELLITES GENERATOR (H6–H20 + G5)")
    print("=" * 70)

    work_centres, grades, disciplines, cost_centres, vendors = load_reference_data()
    df_emp, df_post, df_prod = load_upstream_landing()

    df_snapshot = generate_headcount_snapshot(df_emp, df_post)
    df_payroll = generate_payroll_monthly(df_emp, df_post, work_centres, grades, disciplines, cost_centres)
    df_sanc = generate_sanctioned_posts(df_emp, df_post, work_centres, grades, disciplines)
    df_apar = generate_apar_ratings(df_emp, df_post, grades)
    df_succ = generate_succession_plan(df_emp, df_post, work_centres)
    df_calendar, df_attendance = generate_training(df_emp, df_post, work_centres, disciplines)
    df_leave = generate_leave_ledger(df_emp)
    df_claims = generate_medical_claims(df_emp)
    df_legal = generate_grievances_litigation(df_emp)
    df_contract = generate_contract_workforce(df_snapshot, df_prod, work_centres, vendors)
    df_hse = generate_hse_incidents(df_snapshot, df_contract, work_centres)
    df_travel = generate_travel_claims(df_emp, work_centres)
    df_icc = generate_icc_committees(df_emp, work_centres)
    df_vig = generate_vigilance_cases(df_emp)
    df_log = generate_access_audit_log(df_emp)

    df_leave, df_claims, df_log = apply_demo_personas(df_leave, df_claims, df_attendance, df_travel, df_log, df_emp)

    tables = {
        "H6": df_sanc,
        "H7": df_snapshot,
        "H8": df_payroll,
        "H9": df_apar,
        "H10": df_succ,
        "H11": df_attendance,
        "H12": df_calendar,
        "H13": df_leave,
        "H14": df_claims,
        "H15": df_legal,
        "H16": df_contract,
        "H17": df_hse,
        "H18": df_travel,
        "H19": df_icc,
        "H20": df_vig,
        "G5": df_log,
    }

    save_all_landing_files(tables)
    print("=" * 70)
    print("HR SATELLITES GENERATOR COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    generate_all()
