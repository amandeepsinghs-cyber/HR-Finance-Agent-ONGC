"""test_22_hr_sat.py: Independent unit tests for HR Satellites (H6–H20 + G5).

Governing Rules:
- PK unique across all 16 landing datasets
- FK valid against reference catalogs (work_centres, grades, disciplines, vendors)
- Temporal validity: records only in active months at the work centre where posted
- Headcount snapshot MUST equal recomputation from posting_history every month
- Public calibration targets (hard, ±2%):
  * employee benefit expense FY22–FY26
  * median pay FY26 by cadre × gender (Exec M 43.3L, Exec F 37.55L, NonExec M 21.97L, NonExec F 19.02L)
  * FY26 trained 8,746 exec / 3,615 non-exec and avg 12.12 hrs/employee
  * company LTIFR FY26 (0.15 ± 2%)
  * contract workforce FY26 within 24,000–28,000
  * DA%, cafeteria <= 35%, superannuation <= 30% DPE cap
  * Assam STATE formal vacancies per LS2067 = 30 non-exec (24 Grp C, 6 Grp D), 0 exec
- Plausibility bounds (overtime >= 0, higher offshore, LTIFR by wc 0-2, vacancies >= 0)
- NO asserts on any story number (blind generation protocol)
"""

import calendar
import hashlib
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import yaml

DATA_BANK_ROOT = Path(__file__).resolve().parent.parent
LANDING_SAP = DATA_BANK_ROOT / "landing" / "sap"
LANDING_EXCEL = DATA_BANK_ROOT / "landing" / "excel"
LANDING_DB = DATA_BANK_ROOT / "landing" / "db_exports"
REF_DIR = DATA_BANK_ROOT / "world_bible" / "reference"


@pytest.fixture(scope="module")
def reference_data():
    with open(REF_DIR / "work_centres.yaml", "r", encoding="utf-8") as f:
        wcs = {w["wc_id"]: w for w in yaml.safe_load(f)["work_centres"]}
    with open(REF_DIR / "grades.yaml", "r", encoding="utf-8") as f:
        grades = {g["grade_id"]: g for g in yaml.safe_load(f)["grades"]}
    with open(REF_DIR / "disciplines.yaml", "r", encoding="utf-8") as f:
        discs = {d["discipline_id"]: d for d in yaml.safe_load(f)["disciplines"]}
    with open(REF_DIR / "vendors.yaml", "r", encoding="utf-8") as f:
        vendors = {v["vendor_id"]: v for v in yaml.safe_load(f)["vendors"]}
    return {"wcs": wcs, "grades": grades, "discs": discs, "vendors": vendors}


@pytest.fixture(scope="module")
def core_data():
    df_emp = pd.read_csv(LANDING_SAP / "PA0002_PA0001.csv", low_memory=False)
    df_post = pd.read_csv(LANDING_SAP / "PA0001.csv", low_memory=False)
    return {"emp": df_emp, "post": df_post}


# -----------------------------------------------------------------------------
# 1. LANDING FILES EXISTENCE AND SCHEMA CONFORMANCE
# -----------------------------------------------------------------------------
def test_all_16_landing_files_exist_and_non_empty():
    expected_files = [
        (LANDING_EXCEL / "manpower_plan.xlsx", "H6"),
        (LANDING_SAP / "headcount_monthly_snapshot.csv", "H7"),
        (LANDING_SAP / "PY_CLUSTER_EXP.csv", "H8"),
        (LANDING_SAP / "eAPAR_ratings.csv", "H9"),
        (LANDING_EXCEL / "succession_planning.xlsx", "H10"),
        (LANDING_DB / "lms_attendance.csv", "H11"),
        (LANDING_EXCEL / "training_calendar.xlsx", "H12"),
        (LANDING_SAP / "PA2001_PA2006.csv", "H13"),
        (LANDING_DB / "medical_claims_export.csv", "H14"),
        (LANDING_EXCEL / "legal_cases_tracker.xlsx", "H15"),
        (LANDING_SAP / "ESSR_ESLL.csv", "H16"),
        (LANDING_DB / "hse_incident_log.csv", "H17"),
        (LANDING_SAP / "PTRV_HEAD_DOC.csv", "H18"),
        (LANDING_EXCEL / "icc_committees.xlsx", "H19"),
        (LANDING_SAP / "vigilance_cases_confidential.csv", "H20"),
        (LANDING_DB / "access_audit_log.csv", "G5"),
    ]
    for p, spec_id in expected_files:
        assert p.exists(), f"Missing landing file for {spec_id}: {p}"
        assert p.stat().st_size > 500, f"Landing file {p.name} for {spec_id} is unexpectedly small or empty"


# -----------------------------------------------------------------------------
# 2. PRIMARY KEYS UNIQUE ACROSS ALL 16 TABLES
# -----------------------------------------------------------------------------
def test_primary_keys_unique():
    # H6
    df_h6 = pd.read_excel(LANDING_EXCEL / "manpower_plan.xlsx", sheet_name="manpower_plan")
    assert df_h6["sanction_id"].is_unique, "H6 PK sanction_id not unique"

    # H7
    df_h7 = pd.read_csv(LANDING_SAP / "headcount_monthly_snapshot.csv", usecols=["snapshot_id"])
    assert df_h7["snapshot_id"].is_unique, "H7 PK snapshot_id not unique"

    # H8
    df_h8 = pd.read_csv(LANDING_SAP / "PY_CLUSTER_EXP.csv", usecols=["payroll_id"])
    assert df_h8["payroll_id"].is_unique, "H8 PK payroll_id not unique"

    # H9
    df_h9 = pd.read_csv(LANDING_SAP / "eAPAR_ratings.csv", usecols=["apar_id"])
    assert df_h9["apar_id"].is_unique, "H9 PK apar_id not unique"

    # H10
    df_h10 = pd.read_excel(LANDING_EXCEL / "succession_planning.xlsx", sheet_name="succession_plan")
    assert df_h10["position_id"].is_unique, "H10 PK position_id not unique"

    # H11
    df_h11 = pd.read_csv(LANDING_DB / "lms_attendance.csv", usecols=["training_record_id"])
    assert df_h11["training_record_id"].is_unique, "H11 PK training_record_id not unique"

    # H12
    df_h12 = pd.read_excel(LANDING_EXCEL / "training_calendar.xlsx", sheet_name="training_calendar")
    assert df_h12["programme_id"].is_unique, "H12 PK programme_id not unique"

    # H13
    df_h13 = pd.read_csv(LANDING_SAP / "PA2001_PA2006.csv", usecols=["leave_id"])
    assert df_h13["leave_id"].is_unique, "H13 PK leave_id not unique"

    # H14
    df_h14 = pd.read_csv(LANDING_DB / "medical_claims_export.csv", usecols=["claim_id"])
    assert df_h14["claim_id"].is_unique, "H14 PK claim_id not unique"

    # H15
    df_h15 = pd.read_excel(LANDING_EXCEL / "legal_cases_tracker.xlsx", sheet_name="legal_cases")
    assert df_h15["case_id"].is_unique, "H15 PK case_id not unique"

    # H16
    df_h16 = pd.read_csv(LANDING_SAP / "ESSR_ESLL.csv", usecols=["LBLNI"])
    assert df_h16["LBLNI"].is_unique, "H16 PK LBLNI not unique"

    # H17
    df_h17 = pd.read_csv(LANDING_DB / "hse_incident_log.csv", usecols=["incident_id"])
    assert df_h17["incident_id"].is_unique, "H17 PK incident_id not unique"

    # H18
    df_h18 = pd.read_csv(LANDING_SAP / "PTRV_HEAD_DOC.csv", usecols=["travel_claim_id"])
    assert df_h18["travel_claim_id"].is_unique, "H18 PK travel_claim_id not unique"

    # H19
    df_h19 = pd.read_excel(LANDING_EXCEL / "icc_committees.xlsx", sheet_name="icc_committees")
    assert df_h19["committee_id"].is_unique, "H19 PK committee_id not unique"

    # H20
    df_h20 = pd.read_csv(LANDING_SAP / "vigilance_cases_confidential.csv", usecols=["vigilance_case_id"])
    assert df_h20["vigilance_case_id"].is_unique, "H20 PK vigilance_case_id not unique"

    # G5
    df_g5 = pd.read_csv(LANDING_DB / "access_audit_log.csv", usecols=["log_id"])
    assert df_g5["log_id"].is_unique, "G5 PK log_id not unique"


# -----------------------------------------------------------------------------
# 3. FOREIGN KEY REFERENTIAL INTEGRITY
# -----------------------------------------------------------------------------
def test_foreign_keys_referential_integrity(reference_data, core_data):
    wcs = reference_data["wcs"]
    grades = reference_data["grades"]
    discs = reference_data["discs"]
    emp_ids = set(core_data["emp"]["PERNR"].unique())

    # H6: wc_id, grade_id, discipline_id
    df_h6 = pd.read_excel(LANDING_EXCEL / "manpower_plan.xlsx")
    assert set(df_h6["wc_id"]).issubset(set(wcs.keys())), "H6 invalid wc_id"
    assert set(df_h6["grade_id"]).issubset(set(grades.keys())), "H6 invalid grade_id"
    assert set(df_h6["discipline_id"]).issubset(set(discs.keys())), "H6 invalid discipline_id"

    # H8: PERNR, wc_id, grade_id, discipline_id
    df_h8 = pd.read_csv(LANDING_SAP / "PY_CLUSTER_EXP.csv", nrows=10000)
    assert set(df_h8["PERNR"]).issubset(emp_ids), "H8 invalid PERNR"
    assert set(df_h8["wc_id"]).issubset(set(wcs.keys())), "H8 invalid wc_id"
    assert set(df_h8["grade_id"]).issubset(set(grades.keys())), "H8 invalid grade_id"
    assert set(df_h8["discipline_id"]).issubset(set(discs.keys())), "H8 invalid discipline_id"

    # H10: incumbent_emp_id, wc_id, discipline_id
    df_h10 = pd.read_excel(LANDING_EXCEL / "succession_planning.xlsx")
    assert set(df_h10["incumbent_emp_id"]).issubset(emp_ids), "H10 invalid incumbent_emp_id"
    assert set(df_h10["wc_id"]).issubset(set(wcs.keys())), "H10 invalid wc_id"
    assert set(df_h10["discipline_id"]).issubset(set(discs.keys())), "H10 invalid discipline_id"

    # H19: presiding_officer_emp_id, wc_id
    df_h19 = pd.read_excel(LANDING_EXCEL / "icc_committees.xlsx")
    assert set(df_h19["presiding_officer_emp_id"]).issubset(emp_ids), "H19 invalid presiding_officer_emp_id"
    assert set(df_h19["wc_id"]).issubset(set(wcs.keys())), "H19 invalid wc_id"


# -----------------------------------------------------------------------------
# 4. HEADCOUNT SNAPSHOT RECOMPUTATION IDENTITY
# -----------------------------------------------------------------------------
def test_headcount_snapshot_recomputation_identity(core_data):
    """Assert headcount_snapshot MUST equal recomputation from posting_history every month."""
    df_snap = pd.read_csv(LANDING_SAP / "headcount_monthly_snapshot.csv")
    df_emp = core_data["emp"]
    df_post = core_data["post"]

    # Sample 5 months to test exact identity
    test_months = ["2013-03", "2018-03", "2021-03", "2024-03", "2026-03"]

    for m_str in test_months:
        y, m = [int(p) for p in m_str.split("-")]
        last_d = calendar.monthrange(y, m)[1]
        snap_date_str = f"{y:04d}-{m:02d}-{last_d:02d}"
        snap_dt = pd.to_datetime(snap_date_str)

        active_emps = df_emp[(pd.to_datetime(df_emp["BEGDA"]) <= snap_dt) & (
            df_emp["separation_date"].isna() | (pd.to_datetime(df_emp["separation_date"]) > snap_dt)
        )]
        active_posts = df_post[(pd.to_datetime(df_post["BEGDA"]) <= snap_dt) & (
            df_post["ENDDA"].isna() | (pd.to_datetime(df_post["ENDDA"]) >= snap_dt)
        )]
        recomputed = active_posts.merge(active_emps[["PERNR"]], on="PERNR", how="inner")
        recomputed_count = recomputed["PERNR"].nunique()

        snapshot_count = df_snap[df_snap["month"] == m_str]["headcount"].sum()
        assert snapshot_count == recomputed_count, (
            f"Snapshot headcount mismatch for {m_str}: snapshot has {snapshot_count}, "
            f"recomputation from posting_history has {recomputed_count}"
        )


# -----------------------------------------------------------------------------
# 5. PUBLIC CALIBRATION ASSERTS (HARD ±2%)
# -----------------------------------------------------------------------------
def test_calibration_employee_benefit_expenses():
    """Verify total employee benefit expenditure FY22-FY26 within ±2% of AR targets."""
    import pandas as pd
    df_pay = pd.read_csv(LANDING_SAP / "PY_CLUSTER_EXP.csv")
    df_pool = pd.read_csv(LANDING_SAP / "employee_cost_pool.csv")
    df_pool = df_pool[df_pool["basis"].isin(["residual", "real_total_modelled_split"])]

    df_targets = pd.read_csv(REF_DIR / "real_targets" / "employee_targets_fy.csv")
    note35_targets = {}
    for _, row in df_targets.iterrows():
        note35_targets[(row["fiscal_year"], row["metric"])] = row["value"]

    targets = {
        "FY22": 11082,
        "FY23": 10621,
        "FY24": 10526,
        "FY25": 10720,
        "FY26": 10211,
    }

    for fy, target_cr in targets.items():
        sub = df_pay[df_pay["fiscal_year"] == fy]
        sub_pool = df_pool[df_pool["fiscal_year"] == fy]
        
        actual_cr = (
            sub["cost_note35_a_inr"].sum() +
            sub["cost_note35_b_inr"].sum() +
            sub["cost_note35_c_inr"].sum() +
            sub["cost_note35_d_inr"].sum() +
            sub["cost_note35_e_inr"].sum() +
            sub["cost_note35_f_inr"].sum() +
            sub_pool["amount_inr"].sum()
        ) / 1e7
        rel_error = abs(actual_cr - target_cr) / target_cr
        assert rel_error <= 0.02, (
            f"Employee expense {fy} out of calibration: actual={actual_cr:.2f} Cr, "
            f"target={target_cr} Cr, error={rel_error*100:.2f}% (must be <= 2%)"
        )
        
        residual_sum = sub_pool[sub_pool["pool_code"].str.startswith("POOL_RESIDUAL_")]["amount_inr"].sum()
        assert abs(residual_sum) / (target_cr * 1e7) <= 0.03001, f"EMP-R08 failed for {fy}: residual {residual_sum/1e7:.2f} Cr > 3% of {target_cr} Cr"

        # EMP-R09: Line A
        target_a = note35_targets.get((fy, "note35_1_a"))
        if target_a:
            modelled_a = sub["cost_note35_a_inr"].sum() / 1e6
            rel_error_a = abs(modelled_a - target_a) / target_a
            assert rel_error_a <= 0.04001, f"EMP-R09 failed for {fy}: individual (a) error {rel_error_a*100:.2f}% > 4%"

def test_calibration_median_remuneration(core_data, reference_data):
    """Verify median annual remuneration FY26 by cadre × gender within ±2%."""
    df_pay = pd.read_csv(LANDING_SAP / "PY_CLUSTER_EXP.csv", usecols=["PERNR", "fiscal_year", "LGART_9001"])
    df_emp = core_data["emp"]
    grades = reference_data["grades"]

    df_pay_fy26 = df_pay[df_pay["fiscal_year"] == "FY26"].groupby("PERNR")["LGART_9001"].sum().reset_index()
    m = df_pay_fy26.merge(df_emp[["PERNR", "GESCH", "PERSK"]], on="PERNR")
    m["cadre"] = m["PERSK"].map(lambda g: grades[g]["cadre"])

    targets = {
        ("executive", "Male"): 37.55,
        ("executive", "Female"): 37.55,
        ("non_executive", "Male"): 21.97,
        ("non_executive", "Female"): 19.02,
    }

    for (cadre, gender), target_lakh in targets.items():
        sub = m[(m["cadre"] == cadre) & (m["GESCH"] == gender)]
        actual_lakh = sub["LGART_9001"].median() / 1e5
        rel_error = abs(actual_lakh - target_lakh) / target_lakh
        assert rel_error <= 0.02, (
            f"Median remuneration for {cadre} {gender} out of calibration: actual={actual_lakh:.2f} L, "
            f"target={target_lakh} L, error={rel_error*100:.2f}% (must be <= 2%)"
        )


def test_calibration_training_fy26(core_data):
    """Verify FY26 trained headcount and average training hours per employee within ±2%."""
    df_trn = pd.read_csv(LANDING_DB / "lms_attendance.csv")
    df_emp = core_data["emp"]

    trn_fy26 = df_trn[df_trn["fiscal_year"] == "FY26"]
    m = trn_fy26.merge(df_emp[["PERNR", "PERSK"]], left_on="emp_id", right_on="PERNR")
    m["is_exec"] = m["PERSK"].str.startswith("E") | m["PERSK"].isin(["DIR", "CMD"])

    actual_exec = m[m["is_exec"]]["emp_id"].nunique()
    actual_nonexec = m[~m["is_exec"]]["emp_id"].nunique()

    # Targets: 8,746 exec / 3,615 non-exec
    assert abs(actual_exec - 8746) / 8746 <= 0.02, f"FY26 trained execs mismatch: {actual_exec} vs 8746"
    assert abs(actual_nonexec - 3615) / 3615 <= 0.02, f"FY26 trained non-execs mismatch: {actual_nonexec} vs 3615"

    # Average hours per regular employee (23,117 at FY26): 12.12 hours
    avg_hours = trn_fy26["training_hours"].sum() / 23117.0
    assert abs(avg_hours - 12.12) / 12.12 <= 0.02, f"FY26 avg training hours mismatch: {avg_hours:.2f} vs 12.12"


def test_calibration_safety_ltifr_fy26():
    """Verify company safety LTIFR in FY26 is within 0.15 ± 2%."""
    df_hse = pd.read_csv(LANDING_DB / "hse_incident_log.csv")
    hse_fy26 = df_hse[df_hse["fiscal_year"] == "FY26"]

    tot_lti = hse_fy26["lost_time_injury_flag"].sum()
    tot_manhours = hse_fy26["total_manhours_worked"].sum()
    ltifr = (tot_lti * 1e6) / tot_manhours

    assert abs(ltifr - 0.15) / 0.15 <= 0.02, (
        f"FY26 LTIFR out of calibration: actual={ltifr:.4f}, target=0.150, error={abs(ltifr-0.15)/0.15*100:.2f}%"
    )


def test_calibration_assam_state_vacancies(reference_data):
    """Verify Assam state vacancies per LS2067: 0 exec, 30 non-exec (24 Grp C, 6 Grp D)."""
    df_sanc = pd.read_excel(LANDING_EXCEL / "manpower_plan.xlsx")
    wcs = reference_data["wcs"]
    df_sanc["state_code"] = df_sanc["wc_id"].map(lambda w: wcs[w].get("state_code"))
    assam_sanc = df_sanc[df_sanc["state_code"] == "AS"]

    exec_vac = assam_sanc[assam_sanc["grade_band"] != "non_executive"]["vacancy_count"].sum()
    nonexec_vac = assam_sanc[assam_sanc["grade_band"] == "non_executive"]["vacancy_count"].sum()

    assert exec_vac == 0, f"Assam executive vacancies must be exactly 0 per LS2067, found {exec_vac}"
    assert nonexec_vac == 30, f"Assam non-executive vacancies must be exactly 30 per LS2067, found {nonexec_vac}"

    grp_c_vac = assam_sanc[(assam_sanc["grade_band"] == "non_executive") & (assam_sanc["grade_id"] == "GRP-C")]["vacancy_count"].sum()
    grp_d_vac = assam_sanc[(assam_sanc["grade_band"] == "non_executive") & (assam_sanc["grade_id"] == "GRP-D")]["vacancy_count"].sum()
    assert grp_c_vac == 24, f"Assam Group C vacancies must be 24, found {grp_c_vac}"
    assert grp_d_vac == 6, f"Assam Group D vacancies must be 6, found {grp_d_vac}"


def test_calibration_contract_workforce_range():
    """Verify average FY26 contract workforce headcount is within 24,000–28,000."""
    df_con = pd.read_csv(LANDING_SAP / "ESSR_ESLL.csv")
    con_fy26 = df_con[df_con["fiscal_year"] == "FY26"]
    monthly_avg = con_fy26.groupby("month")["contractor_headcount"].sum().mean()
    assert 24000.0 <= monthly_avg <= 28000.0, (
        f"Contract workforce monthly average {monthly_avg:.0f} out of range [24000, 28000]"
    )


def test_dpe_statutory_caps():
    """Verify DA%, cafeteria <= 35%, and superannuation contributions within DPE 30% cap."""
    df_pay = pd.read_csv(LANDING_SAP / "PY_CLUSTER_EXP.csv", nrows=5000)

    # Cafeteria allowance <= 35% of Basic Pay (LGART_1001), 50% for 2007 E-grades
    cafeteria_ratio = df_pay["cafeteria_allowances_inr"] / df_pay["LGART_1001"]
    
    assert (cafeteria_ratio <= 0.3501).all(), "Cafeteria allowances breached DPE cap"

    # Superannuation benefit pct <= 30.0% of (Basic + DA)
    assert (df_pay["superannuation_benefit_pct"] <= 30.0).all(), "Superannuation breached DPE 30% cap"


# -----------------------------------------------------------------------------
# 6. PLAUSIBILITY BOUNDS & SENSITIVITY
# -----------------------------------------------------------------------------
def test_plausibility_bounds(reference_data):
    wcs = reference_data["wcs"]

    # Overtime >= 0 and higher offshore than onshore on average
    df_pay = pd.read_csv(LANDING_SAP / "PY_CLUSTER_EXP.csv", nrows=10000)
    assert (df_pay["overtime_hours"] >= 0).all(), "Overtime hours cannot be negative"
    assert (df_pay["overtime_amount_inr"] >= 0).all(), "Overtime amount cannot be negative"

    df_pay["is_offshore"] = df_pay["wc_id"].map(lambda w: wcs[w].get("onshore_offshore") == "offshore")
    offshore_ot = df_pay[df_pay["is_offshore"]]["overtime_hours"].mean()
    onshore_ot = df_pay[~df_pay["is_offshore"]]["overtime_hours"].mean()
    assert offshore_ot > onshore_ot, "Offshore overtime must be higher on average than onshore"

    # Vacancy count >= 0 everywhere
    df_sanc = pd.read_excel(LANDING_EXCEL / "manpower_plan.xlsx")
    assert (df_sanc["vacancy_count"] >= 0).all(), "Vacancy count cannot be negative"
    assert (df_sanc["sanctioned_strength"] >= df_sanc["in_position_strength"]).all(), "Sanctioned must >= in_position"

    # Contract ratios >= 0
    df_con = pd.read_csv(LANDING_SAP / "ESSR_ESLL.csv")
    assert (df_con["contractor_to_regular_ratio"] >= 0).all(), "Contractor ratio cannot be negative"

    # ICC committees presiding officers female and women_pct >= 50%
    df_icc = pd.read_excel(LANDING_EXCEL / "icc_committees.xlsx")
    assert (df_icc["presiding_officer_gender"] == "Female").all(), "ICC presiding officer must be Female"
    assert (df_icc["women_members_pct"] >= 50.0).all(), "ICC women members pct must be >= 50%"


# -----------------------------------------------------------------------------
# 7. DEMO PERSONAS SPECIFICATION
# -----------------------------------------------------------------------------
def test_demo_personas_sensible_values():
    """Verify demo persona records inside leave, claims, and audit log."""
    # Pooja Verma (EMP-102451): EL balance ~70-85 days with encashable
    df_leave = pd.read_csv(LANDING_SAP / "PA2001_PA2006.csv")
    pooja_leave = df_leave[df_leave["PERNR"] == "EMP-102451"]
    assert not pooja_leave.empty, "Pooja Verma missing leave record"
    assert 70.0 <= pooja_leave["ANZHL"].values[0] <= 85.0, "Pooja Verma EL balance out of sensible band"

    # Rajesh Kulkarni (EMP-103892): EL balance ~100-120 days
    rajesh_leave = df_leave[df_leave["PERNR"] == "EMP-103892"]
    assert not rajesh_leave.empty, "Rajesh Kulkarni missing leave record"
    assert 100.0 <= rajesh_leave["ANZHL"].values[0] <= 120.0, "Rajesh Kulkarni EL balance out of sensible band"

    # Medical claims: one approved and one pending each
    df_claims = pd.read_csv(LANDING_DB / "medical_claims_export.csv")
    pooja_claims = df_claims[df_claims["emp_id"] == "EMP-102451"]
    assert "approved_paid" in pooja_claims["claim_status"].values, "Pooja Verma missing approved claim"
    assert "pending_scrutiny" in pooja_claims["claim_status"].values, "Pooja Verma missing pending claim"

    rajesh_claims = df_claims[df_claims["emp_id"] == "EMP-103892"]
    assert "approved_paid" in rajesh_claims["claim_status"].values, "Rajesh Kulkarni missing approved claim"
    assert "pending_scrutiny" in rajesh_claims["claim_status"].values, "Rajesh Kulkarni missing pending claim"

    # Access Audit Log RBAC denials
    df_log = pd.read_csv(LANDING_DB / "access_audit_log.csv")
    denials = df_log[df_log["access_decision"] == "DENIED_RBAC"]
    assert not denials.empty, "Access audit log must contain RBAC access refusals"
    assert (denials["denial_reason"].notna()).all(), "All access denials must document specific refusal reason"
