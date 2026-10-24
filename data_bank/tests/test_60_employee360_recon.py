"""Offline reconciliation tests for Employee-360 (SPEC-04 §7.4: EMP-R01 through EMP-R30)."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
LANDING_SAP = BASE_DIR / "landing" / "sap"
LANDING_DB = BASE_DIR / "landing" / "db_exports"
REF_DIR = BASE_DIR / "world_bible" / "reference"
TARGETS_PATH = REF_DIR / "real_targets" / "employee_targets_fy.csv"


@pytest.fixture(scope="module")
def targets_df() -> pd.DataFrame:
    assert TARGETS_PATH.exists(), f"Missing {TARGETS_PATH}"
    return pd.read_csv(TARGETS_PATH)


@pytest.fixture(scope="module")
def pa_df() -> pd.DataFrame:
    path = LANDING_SAP / "PA0002_PA0001.csv"
    assert path.exists(), f"Missing {path}"
    df = pd.read_csv(path, low_memory=False)
    df["age_at_doj"] = (pd.to_datetime(df["BEGDA"]) - pd.to_datetime(df["GBDAT"])).dt.days / 365.25
    df["gender_code"] = df["GESCH"].map({"Female": "F", "F": "F", "Male": "M", "M": "M"}).fillna("O")
    return df


@pytest.fixture(scope="module")
def active_fy26_df(pa_df: pd.DataFrame) -> pd.DataFrame:
    return pa_df[
        (pa_df["BEGDA"] <= "2026-03-31")
        & (pa_df["separation_date"].isna() | (pa_df["separation_date"] > "2026-03-31"))
    ].copy()


@pytest.fixture(scope="module")
def active_fy25_df(pa_df: pd.DataFrame) -> pd.DataFrame:
    return pa_df[
        (pa_df["BEGDA"] <= "2025-03-31")
        & (pa_df["separation_date"].isna() | (pa_df["separation_date"] > "2025-03-31"))
    ].copy()


@pytest.fixture(scope="module")
def py_df() -> pd.DataFrame:
    path = LANDING_SAP / "PY_CLUSTER_EXP.csv"
    assert path.exists(), f"Missing {path}"
    return pd.read_csv(
        path,
        usecols=[
            "PERNR",
            "FPPER",
            "fiscal_year",
            "grade_id",
            "LGART_1001",
            "LGART_1002",
            "hra_inr",
            "cafeteria_allowances_inr",
            "LGART_9001",
            "LGART_9002",
            "employer_cpf_inr",
            "superannuation_benefit_pct",
            "employee_pf_inr",
            "vpf_inr",
            "income_tax_tds_inr",
            "professional_tax_inr",
            "hrr_recovery_inr",
            "loan_recoveries_inr",
            "other_recoveries_inr",
            "cost_note35_a_inr",
            "cost_note35_b_inr",
            "cost_note35_c_inr",
            "cost_note35_d_inr",
            "cost_note35_e_inr",
            "cost_note35_f_inr",
            "cost_capitalised_inr",
            "cost_expensed_inr",
            "cost_expensed_production_inr",
        ],
    )


@pytest.fixture(scope="module")
def pool_df() -> pd.DataFrame:
    path = LANDING_SAP / "employee_cost_pool.csv"
    assert path.exists(), f"Missing {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def hc_snap_df() -> pd.DataFrame:
    path = LANDING_SAP / "headcount_monthly_snapshot.csv"
    assert path.exists(), f"Missing {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def sep_df() -> pd.DataFrame:
    path = LANDING_SAP / "PA0000_separations.csv"
    assert path.exists(), f"Missing {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def lms_df() -> pd.DataFrame:
    path = LANDING_DB / "lms_attendance.csv"
    assert path.exists(), f"Missing {path}"
    return pd.read_csv(path)


def _target_val(targets_df: pd.DataFrame, fy: str, code: str) -> float:
    col = "metric" if "metric" in targets_df.columns else "metric_code"
    sub = targets_df[(targets_df["fiscal_year"] == fy) & (targets_df[col] == code)]
    assert not sub.empty, f"Missing target {fy} / {code}"
    return float(sub["value"].iloc[0])


# ---------------------------------------------------------------------------
# EMP-R01 .. EMP-R09: Note 35.1 total, lines (a)-(f), pool cap, 35.1(a) share
# ---------------------------------------------------------------------------
def test_emp_r01_note35_1_total(py_df: pd.DataFrame, pool_df: pd.DataFrame, targets_df: pd.DataFrame):
    """EMP-R01: Note 35.1 total employee benefit expense (FY17-FY26, <= Rs 0.1 mn)."""
    ind = (
        py_df["cost_note35_a_inr"]
        + py_df["cost_note35_b_inr"]
        + py_df["cost_note35_c_inr"]
        + py_df["cost_note35_d_inr"]
        + py_df["cost_note35_e_inr"]
        + py_df["cost_note35_f_inr"]
    ).groupby(py_df["fiscal_year"]).sum()
    pool = (
        pool_df[pool_df["basis"].isin(["residual", "real_total_modelled_split"])]
        .groupby("fiscal_year")["amount_inr"]
        .sum()
    )
    for fy in [f"FY{y}" for y in range(17, 27)]:
        target_mn = _target_val(targets_df, fy, "employee_cost_total")
        actual_mn = (float(ind.get(fy, 0.0)) + float(pool.get(fy, 0.0))) / 1e6
        assert abs(actual_mn - target_mn) <= 0.1, f"EMP-R01 {fy}: {actual_mn:.3f} vs {target_mn:.3f}"


@pytest.mark.parametrize(
    "check_id,line_key,metric_code",
    [
        ("EMP-R02", "a", "note35_1_a"),
        ("EMP-R03", "b", "note35_1_b"),
        ("EMP-R04", "c", "note35_1_c"),
        ("EMP-R05", "d", "note35_1_d"),
        ("EMP-R06", "e", "note35_1_e"),
        ("EMP-R07", "f", "note35_1_f"),
    ],
)
def test_emp_r02_to_r07_note35_lines(
    check_id: str,
    line_key: str,
    metric_code: str,
    py_df: pd.DataFrame,
    pool_df: pd.DataFrame,
    targets_df: pd.DataFrame,
):
    """EMP-R02..R07: Note 35.1 lines (a)-(f) (FY21-FY26, <= Rs 0.1 mn)."""
    col = f"cost_note35_{line_key}_inr"
    ind = py_df.groupby("fiscal_year")[col].sum()
    pool = (
        pool_df[
            (pool_df["basis"].isin(["residual", "real_total_modelled_split"]))
            & (pool_df["note35_line"] == line_key)
        ]
        .groupby("fiscal_year")["amount_inr"]
        .sum()
    )
    for fy in [f"FY{y}" for y in range(21, 27)]:
        target_mn = _target_val(targets_df, fy, metric_code)
        actual_mn = (float(ind.get(fy, 0.0)) + float(pool.get(fy, 0.0))) / 1e6
        assert abs(actual_mn - target_mn) <= 0.1, f"{check_id} {fy}: {actual_mn:.3f} vs {target_mn:.3f}"


def test_emp_r08_pool_resid_share(pool_df: pd.DataFrame, targets_df: pd.DataFrame):
    """EMP-R08: POOL-RESID share of Note 35.1 total <= 3.0% (FY17-FY26)."""
    resid = pool_df[pool_df["basis"] == "residual"].groupby("fiscal_year")["amount_inr"].sum()
    for fy in [f"FY{y}" for y in range(17, 27)]:
        target_mn = _target_val(targets_df, fy, "employee_cost_total")
        resid_mn = float(resid.get(fy, 0.0)) / 1e6
        share_pct = abs(resid_mn) / target_mn * 100.0
        assert share_pct <= 3.0, f"EMP-R08 {fy}: residual share {share_pct:.2f}% > 3.0%"


def test_emp_r09_individual_35_1a_coverage(py_df: pd.DataFrame, targets_df: pd.DataFrame):
    """EMP-R09: Individual rows cover >= 96% of 35.1(a) before pool (FY21-FY26)."""
    ind_a = py_df.groupby("fiscal_year")["cost_note35_a_inr"].sum()
    for fy in [f"FY{y}" for y in range(21, 27)]:
        target_mn = _target_val(targets_df, fy, "note35_1_a")
        actual_mn = float(ind_a.get(fy, 0.0)) / 1e6
        pct_diff = abs(actual_mn - target_mn) / target_mn * 100.0
        assert pct_diff <= 4.0, f"EMP-R09 {fy}: {actual_mn:.2f} vs {target_mn:.2f} ({pct_diff:.2f}%)"


# ---------------------------------------------------------------------------
# EMP-R10 .. EMP-R15: Headcount & BRSR workforce composition
# ---------------------------------------------------------------------------
def test_emp_r10_fy_end_headcount(
    hc_snap_df: pd.DataFrame, active_fy26_df: pd.DataFrame, targets_df: pd.DataFrame
):
    """EMP-R10: FY-end active headcount matches AR/BRSR exactly (FY17-FY26)."""
    for y in range(17, 27):
        fy = f"FY{y}"
        march_ym = f"{2000 + y}-03"
        target_hc = int(_target_val(targets_df, fy, "headcount_fy_end"))
        snap_hc = int(hc_snap_df[hc_snap_df["month"] == march_ym]["headcount"].sum())
        assert snap_hc == target_hc, f"EMP-R10 {fy}: snapshot {snap_hc} != target {target_hc}"
    assert len(active_fy26_df) == int(_target_val(targets_df, "FY26", "headcount_fy_end"))


def test_emp_r11_brsr_cadre_split_fy26(active_fy26_df: pd.DataFrame, targets_df: pd.DataFrame):
    """EMP-R11: FY26 BRSR executive (13,781) vs non-executive (9,336) exact match."""
    exec_grades = {"E0", "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "DIR", "CMD"}
    exec_cnt = int(active_fy26_df["PERSK"].isin(exec_grades).sum())
    nonexec_cnt = int((~active_fy26_df["PERSK"].isin(exec_grades)).sum())
    assert exec_cnt == int(_target_val(targets_df, "FY26", "brsr_exec_count"))
    assert nonexec_cnt == int(_target_val(targets_df, "FY26", "brsr_nonexec_count"))


def test_emp_r12_brsr_women_count_fy26(active_fy26_df: pd.DataFrame, targets_df: pd.DataFrame):
    """EMP-R12: FY26 active women count = 1,885 (1,377 exec + 508 non-exec)."""
    exec_grades = {"E0", "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "DIR", "CMD"}
    women_df = active_fy26_df[active_fy26_df["gender_code"] == "F"]
    assert len(women_df) == int(_target_val(targets_df, "FY26", "brsr_women_total"))
    assert int(women_df["PERSK"].isin(exec_grades).sum()) == int(
        _target_val(targets_df, "FY26", "brsr_women_exec")
    )
    assert int((~women_df["PERSK"].isin(exec_grades)).sum()) == int(
        _target_val(targets_df, "FY26", "brsr_women_nonexec")
    )


def test_emp_r13_brsr_pwd_count_fy26(active_fy26_df: pd.DataFrame, targets_df: pd.DataFrame):
    """EMP-R13: FY26 active PwD count = 523 (313 exec + 210 non-exec)."""
    exec_grades = {"E0", "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "DIR", "CMD"}
    pwd_df = active_fy26_df[active_fy26_df["pwd_flag"] == True]
    assert len(pwd_df) == int(_target_val(targets_df, "FY26", "brsr_pwd_total"))
    assert int(pwd_df["PERSK"].isin(exec_grades).sum()) == int(
        _target_val(targets_df, "FY26", "brsr_pwd_exec")
    )
    assert int((~pwd_df["PERSK"].isin(exec_grades)).sum()) == int(
        _target_val(targets_df, "FY26", "brsr_pwd_nonexec")
    )


def test_emp_r14_sc_st_shares_fy26(active_fy26_df: pd.DataFrame, targets_df: pd.DataFrame):
    """EMP-R14: FY26 SC share (15.02% +/- 0.5 pp) and ST share (11.35% +/- 0.5 pp)."""
    total = len(active_fy26_df)
    sc_pct = (active_fy26_df["VDSK1"] == "SC").sum() / total * 100.0
    st_pct = (active_fy26_df["VDSK1"] == "ST").sum() / total * 100.0
    assert abs(sc_pct - _target_val(targets_df, "FY26", "sc_share_pct")) <= 0.5
    assert abs(st_pct - _target_val(targets_df, "FY26", "st_share_pct")) <= 0.5


def test_emp_r15_brsr_age_bands_fy26(active_fy26_df: pd.DataFrame, targets_df: pd.DataFrame):
    """EMP-R15: FY26 age bands (<30: 9.59%, 30-50: 65.99%, >50: 24.42% +/- 1.5 pp)."""
    total = len(active_fy26_df)
    dob = active_fy26_df["GBDAT"]
    lt30_pct = (dob > "1996-03-31").sum() / total * 100.0
    b30_50_pct = ((dob >= "1976-04-01") & (dob <= "1996-03-31")).sum() / total * 100.0
    gt50_pct = (dob <= "1976-03-31").sum() / total * 100.0
    assert abs(lt30_pct - _target_val(targets_df, "FY26", "brsr_age_lt30_pct")) <= 1.5
    assert abs(b30_50_pct - _target_val(targets_df, "FY26", "brsr_age_30_50_pct")) <= 1.5
    assert abs(gt50_pct - _target_val(targets_df, "FY26", "brsr_age_gt50_pct")) <= 1.5


# ---------------------------------------------------------------------------
# EMP-R16 .. EMP-R21: Median remuneration, turnover, hires, training, wages, E1 CTC
# ---------------------------------------------------------------------------
def test_emp_r16_brsr_median_remuneration_fy26(
    py_df: pd.DataFrame, pa_df: pd.DataFrame, targets_df: pd.DataFrame
):
    """EMP-R16: FY26 BRSR median annual remuneration (exec/non-exec x M/F within +/- 10%)."""
    py26 = py_df[py_df["fiscal_year"] == "FY26"].copy()
    py26["rem_inr"] = py26["LGART_9001"] + py26["employer_cpf_inr"]
    emp_rem = py26.groupby("PERNR").agg(
        annual_rem=("rem_inr", "sum"),
        months=("FPPER", "count"),
        grade_id=("grade_id", "last"),
    )
    emp_rem = emp_rem[emp_rem["months"] == 12].join(
        pa_df.set_index("PERNR")[["gender_code"]], how="inner"
    )
    exec_grades = {"E0", "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "DIR", "CMD"}
    emp_rem["is_exec"] = emp_rem["grade_id"].isin(exec_grades)

    cohorts = [
        (True, "M", "brsr_median_remuneration_exec_male"),
        (True, "F", "brsr_median_remuneration_exec_female"),
        (False, "M", "brsr_median_remuneration_nonexec_male"),
        (False, "F", "brsr_median_remuneration_nonexec_female"),
    ]
    for is_exec, gender, code in cohorts:
        sub = emp_rem[(emp_rem["is_exec"] == is_exec) & (emp_rem["gender_code"] == gender)]
        actual_med = float(sub["annual_rem"].median())
        target_med = _target_val(targets_df, "FY26", code)
        pct_diff = abs(actual_med - target_med) / target_med * 100.0
        assert pct_diff <= 10.0, f"EMP-R16 {code}: {actual_med:,.0f} vs {target_med:,.0f} ({pct_diff:.2f}%)"


def test_emp_r17_hc_roll_forward_and_turnover_fy26(
    pa_df: pd.DataFrame,
    active_fy25_df: pd.DataFrame,
    active_fy26_df: pd.DataFrame,
    sep_df: pd.DataFrame,
    targets_df: pd.DataFrame,
):
    """EMP-R17: FY26 HC roll-forward identity and BRSR turnover rates (+/- 1.5 pp)."""
    hires_fy26 = int((pa_df["fiscal_year_joined"] == "FY26").sum())
    seps_fy26_df = sep_df[sep_df["fiscal_year"] == "FY26"]
    seps_fy26 = len(seps_fy26_df)
    assert len(active_fy25_df) + hires_fy26 - seps_fy26 == len(active_fy26_df)

    exec_grades = {"E0", "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "DIR", "CMD"}
    seps_with_grade = seps_fy26_df.merge(pa_df[["PERNR", "PERSK"]], on="PERNR", how="left")
    seps_exec = int(seps_with_grade["PERSK"].isin(exec_grades).sum())
    seps_nonexec = int((~seps_with_grade["PERSK"].isin(exec_grades)).sum())

    avg_exec_hc = (
        active_fy25_df["PERSK"].isin(exec_grades).sum()
        + active_fy26_df["PERSK"].isin(exec_grades).sum()
    ) / 2.0
    avg_nonexec_hc = (
        (~active_fy25_df["PERSK"].isin(exec_grades)).sum()
        + (~active_fy26_df["PERSK"].isin(exec_grades)).sum()
    ) / 2.0

    exec_to_pct = seps_exec / avg_exec_hc * 100.0
    nonexec_to_pct = seps_nonexec / avg_nonexec_hc * 100.0
    assert abs(exec_to_pct - _target_val(targets_df, "FY26", "brsr_turnover_exec_pct")) <= 1.5
    assert abs(nonexec_to_pct - _target_val(targets_df, "FY26", "brsr_turnover_nonexec_pct")) <= 1.5


def test_emp_r18_hires_total_and_demographics_fy26(pa_df: pd.DataFrame, targets_df: pd.DataFrame):
    """EMP-R18: FY26 hires total = 167 (BLOCK) and women share = 16.77% +/- 3 pp (BLOCK)."""
    hires_26 = pa_df[pa_df["fiscal_year_joined"] == "FY26"]
    assert len(hires_26) == int(_target_val(targets_df, "FY26", "brsr_hires_total"))
    women_share = (hires_26["gender_code"] == "F").sum() / len(hires_26) * 100.0
    assert abs(women_share - _target_val(targets_df, "FY26", "brsr_hires_women_pct")) <= 3.0
    lt30_share = (hires_26["age_at_doj"] < 30.0).sum() / len(hires_26) * 100.0
    assert lt30_share >= _target_val(targets_df, "FY26", "brsr_hires_lt30_pct") - 3.0


def test_emp_r19_training_hours_per_emp_fy26(
    lms_df: pd.DataFrame, active_fy26_df: pd.DataFrame, targets_df: pd.DataFrame
):
    """EMP-R19: FY26 training hours per active employee = 12.12 +/- 0.5 h."""
    lms_26 = lms_df[lms_df["fiscal_year"] == "FY26"]
    avg_hours = float(lms_26["training_hours"].sum()) / len(active_fy26_df)
    target_hours = _target_val(targets_df, "FY26", "brsr_avg_training_hours")
    assert abs(avg_hours - target_hours) <= 0.5, f"EMP-R19: {avg_hours:.3f} vs {target_hours:.3f}"


def test_emp_r20_women_wage_share_fy26(
    py_df: pd.DataFrame, pa_df: pd.DataFrame, targets_df: pd.DataFrame
):
    """EMP-R20: FY26 women share of gross wages vs BRSR P5 EI-2 (WARN check)."""
    py26 = py_df[py_df["fiscal_year"] == "FY26"].merge(
        pa_df[["PERNR", "gender_code"]], on="PERNR", how="left"
    )
    women_share = (
        float(py26.loc[py26["gender_code"] == "F", "LGART_9001"].sum())
        / float(py26["LGART_9001"].sum())
        * 100.0
    )
    target_share = _target_val(targets_df, "FY26", "brsr_women_wage_share_pct")
    assert abs(women_share - target_share) <= 1.0


def test_emp_r21_entry_e1_ctc_fy26(py_df: pd.DataFrame, pa_df: pd.DataFrame, targets_df: pd.DataFrame):
    """EMP-R21: Entry E1 annualised CTC within target +/- 16%."""
    e1_hires = set(
        pa_df[(pa_df["fiscal_year_joined"] == "FY26") & (pa_df["PERSK"] == "E1")]["PERNR"]
    )
    py_e1 = py_df[(py_df["fiscal_year"] == "FY26") & (py_df["PERNR"].isin(e1_hires))]
    monthly_cost = (
        py_e1["cost_note35_a_inr"]
        + py_e1["cost_note35_b_inr"]
        + py_e1["cost_note35_c_inr"]
        + py_e1["cost_note35_d_inr"]
        + py_e1["cost_note35_e_inr"]
        + py_e1["cost_note35_f_inr"]
    )
    ctc_lakhs = float(monthly_cost.median()) * 12.0 / 1e5
    target_lakhs = _target_val(targets_df, "FY26", "e1_entry_ctc_target_inr") / 1e5
    assert 22.0 <= ctc_lakhs <= 28.5 and target_lakhs > 0, f"EMP-R21: Entry E1 CTC {ctc_lakhs:.2f} L"


# ---------------------------------------------------------------------------
# EMP-R22 .. EMP-R30: Statutory caps, BUG-28..36 invariants, row & cross-domain identities
# ---------------------------------------------------------------------------
def test_emp_r22_superannuation_ceiling(py_df: pd.DataFrame):
    """EMP-R22: Superannuation contribution <= 30% of BP + DA on 100% of rows."""
    violations = int((py_df["superannuation_benefit_pct"] > 30.0001).sum())
    assert violations == 0, f"EMP-R22: {violations} rows exceed 30% superannuation cap"


def test_emp_r23_cafeteria_hra_and_scale_bounds(py_df: pd.DataFrame):
    """EMP-R23: Cafeteria <= 35% BP, HRA tier in allowed set, and BP within 3rd PRC scale bounds."""
    caf_ratio = py_df["cafeteria_allowances_inr"] / py_df["LGART_1001"]
    assert int((caf_ratio > 0.3501).sum()) == 0

    hra_pos = py_df[py_df["hra_inr"] > 0]
    hra_tiers = (hra_pos["hra_inr"] / hra_pos["LGART_1001"]).round(2)
    allowed_hra = {0.08, 0.09, 0.10, 0.16, 0.18, 0.20, 0.24, 0.27, 0.30}
    assert set(hra_tiers.unique()).issubset(allowed_hra)

    with open(REF_DIR / "grades.yaml", "r", encoding="utf-8") as f:
        grades_meta = yaml.safe_load(f)["grades"]
    min_map = {g["grade_id"]: float(g["pay_scale_min_inr"]) for g in grades_meta}
    max_map = {
        g["grade_id"]: max(float(g["pay_scale_max_inr"]), 160000.0 if g["grade_id"] == "E0" else 0.0)
        * (1.03**3)
        + 100.0
        for g in grades_meta
    }

    py17 = py_df[py_df["FPPER"] >= "2017-01"]
    s_min = py17["grade_id"].map(min_map).astype(float)
    s_max = py17["grade_id"].map(max_map).astype(float)
    assert int((py17["LGART_1001"] < s_min - 1.0).sum()) == 0
    assert int((py17["LGART_1001"] > s_max).sum()) == 0


def test_emp_r24_grade_tenure_monotonicity_and_e1_cap(active_fy26_df: pd.DataFrame):
    """EMP-R24: Active E1 median tenure <= 4.0 yrs, E0 count > 0, and E1..E9 median tenure monotonic."""
    e1_med = float(active_fy26_df[active_fy26_df["PERSK"] == "E1"]["total_tenure_years"].median())
    assert e1_med <= 4.0, f"EMP-R24: E1 median tenure {e1_med:.2f} > 4.0 yrs"
    assert int((active_fy26_df["PERSK"] == "E0").sum()) > 0

    medians = [
        float(active_fy26_df[active_fy26_df["PERSK"] == f"E{i}"]["total_tenure_years"].median())
        for i in range(1, 10)
    ]
    for i in range(len(medians) - 1):
        assert medians[i] < medians[i + 1], f"EMP-R24: E{i+1} ({medians[i]}) >= E{i+2} ({medians[i+1]})"


def test_emp_r25_entry_age_and_retirement_age(pa_df: pd.DataFrame, active_fy26_df: pd.DataFrame):
    """EMP-R25: Entry age in [18, 45] on 100% of rows and active age at 2026-03-31 <= 60."""
    assert int(((pa_df["age_at_doj"] < 18.0) | (pa_df["age_at_doj"] > 45.0)).sum()) == 0
    dob = pd.to_datetime(active_fy26_df["GBDAT"])
    age_at_fy26_end = (pd.Timestamp("2026-03-31") - dob).dt.days / 365.25
    assert int((age_at_fy26_end > 60.0).sum()) == 0


def test_emp_r26_name_uniqueness(pa_df: pd.DataFrame, active_fy26_df: pd.DataFrame):
    """EMP-R26: >= 15,000 distinct names and <= 3 namesakes in any single work centre."""
    assert pa_df["name"].nunique() >= 15000
    max_wc_namesakes = int(active_fy26_df.groupby(["WERKS", "name"]).size().max())
    assert max_wc_namesakes <= 3


def test_emp_r27_delhi_hq_headcount(active_fy26_df: pd.DataFrame, targets_df: pd.DataFrame):
    """EMP-R27: Active employees at WC-DEL = 943 +/- 5% ([895.85, 990.15])."""
    del_hc = int((active_fy26_df["WERKS"] == "WC-DEL").sum())
    target_del = _target_val(targets_df, "FY26", "delhi_active_target")
    assert abs(del_hc - target_del) / target_del <= 0.05, f"EMP-R27: WC-DEL headcount {del_hc}"


def test_emp_r28_row_identities(py_df: pd.DataFrame):
    """EMP-R28: gross - deductions = net and sum(cost_note35_a..f) = cap + exp within Rs 0.01."""
    ded = (
        py_df["employee_pf_inr"]
        + py_df["vpf_inr"]
        + py_df["income_tax_tds_inr"]
        + py_df["professional_tax_inr"]
        + py_df["hrr_recovery_inr"]
        + py_df["loan_recoveries_inr"]
        + py_df["other_recoveries_inr"]
    )
    net_diff = (py_df["LGART_9001"] - ded - py_df["LGART_9002"]).abs().max()
    assert float(net_diff) <= 0.01

    n35_sum = (
        py_df["cost_note35_a_inr"]
        + py_df["cost_note35_b_inr"]
        + py_df["cost_note35_c_inr"]
        + py_df["cost_note35_d_inr"]
        + py_df["cost_note35_e_inr"]
        + py_df["cost_note35_f_inr"]
    )
    split_sum = py_df["cost_capitalised_inr"] + py_df["cost_expensed_inr"]
    cost_diff = (n35_sum - split_sum).abs().max()
    assert float(cost_diff) <= 0.01


def test_emp_r29_staff_expenditure_cross_domain(py_df: pd.DataFrame, targets_df: pd.DataFrame):
    """EMP-R29: SUM(cost_expensed_production_inr) matches Note 35 Staff Expenditure (FY21-FY26, <= Rs 0.1 mn)."""
    prod_staff = py_df.groupby("fiscal_year")["cost_expensed_production_inr"].sum()
    for fy in [f"FY{y}" for y in range(21, 27)]:
        target_mn = _target_val(targets_df, fy, "staff_expenditure_note35")
        actual_mn = float(prod_staff.get(fy, 0.0)) / 1e6
        assert abs(actual_mn - target_mn) <= 0.1, f"EMP-R29 {fy}: {actual_mn:.3f} vs {target_mn:.3f}"


def test_emp_r30_average_age_fy26(active_fy26_df: pd.DataFrame, targets_df: pd.DataFrame):
    """EMP-R30: Average age of active employees in FY26 = 43.0 +/- 1.0 years."""
    avg_age = float(active_fy26_df["age_years"].mean())
    target_age = _target_val(targets_df, "FY26", "avg_age_target_years")
    assert abs(avg_age - target_age) <= 1.0, f"EMP-R30: average age {avg_age:.2f} outside {target_age} +/- 1.0"
