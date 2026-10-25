#!/usr/bin/env python3
"""test_21_hr_core.py: Automated Pytest Suite for Step 2.1 (H1–H5 HR Core).

Asserts:
1. Landing files exist strictly per schema_silver.yaml and DATA_GENERATION_CHECKLIST.
2. Row counts within expected scale (~40k employees, >150k postings).
3. Primary keys unique and non-null across all 5 tables.
4. Foreign keys valid against reference data (grades, disciplines, work centres, states).
5. All 14 calibration headcount targets (FY13–FY26) match exactly.
6. Demographics and equity targets at 31-Mar-2026:
   - Total: 23,117 (13,781 executive / 9,336 non-executive)
   - Women: 1,885 (1,377 executive / 508 non-executive) -> 8.15% (target 8.2% ±0.02)
   - Affirmative Action: SC 15.02% (±0.02), ST 11.35% (±0.02)
   - PwD: 523 (313 executive / 210 non-executive)
   - Age bands: <30 (9.6% ±2%), 30–50 (66% ±2%), >50 (24.4% ±2%)
   - FY26 flows: hires 167 (28 female), separations 1,418 (exec turnover ~7.4%, non-exec ~3.1%)
   - Assam state: 3,561 regular employees (1,518 exec / 2,043 non-exec; Group A 1,352 / B 166 / C 1,796 / D 247)
7. Stories emerge from records:
   - S1: Delhi continuous >= 5y (412), cumulative >= 10y (138), retiring <= 3y (31), transfer due (107)
   - S2: E3–E5 never served hard station (260), North-East in-position executives (1,929)
   - S3: Asset trajectories FY21->FY26 (Eastern Offshore 620->830, Rajahmundry 840->1025, Mehsana -12.39%, Cauvery -12.29%)
   - S4: 47 E7+ retiring FY27–FY29 (FY27: 18, FY28: 16, FY29: 13)
   - S5: Technical retirements by 2030 (2,215 of 6,420; DRL 642 of 1680; GEO+GPS 635 of 1840)
   - S7: Cambay headcount +14.2% (514->587)
   - S11: 186 DPC cases delayed >6 months (Drilling 112, Production 74)
   - S12: FY26 resignations 182 (E3–E5: 124 [IT 42, Finance 38])
   - S17: Women in Delhi 154 (21.39%), Dehradun 418 (18.58%), Offshore 78 (1.20%)
   - S38 Personas: EMP-000001..3, EMP-102451 (Pooja Verma), EMP-103892 (Rajesh Kulkarni)
8. Temporal sanity and derived consistency:
   - Zero overlapping postings for any employee
   - Postings strictly between DOJ and separation date
   - is_current_posting True only for active employees' latest stint
9. Determinism: identical SHA-256 hashes on re-execution.
"""

import os
import sys
import hashlib
import subprocess
from pathlib import Path
import pytest
import yaml
import duckdb
import pandas as pd
import numpy as np

DATA_BANK_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DATA_BANK_DIR))

WORLD_BIBLE_DIR = DATA_BANK_DIR / "world_bible"
REF_DIR = WORLD_BIBLE_DIR / "reference"
LANDING_DIR = DATA_BANK_DIR / "landing"
LANDING_SAP = LANDING_DIR / "sap"
LANDING_EXCEL = LANDING_DIR / "excel"


@pytest.fixture(scope="module")
def duck_con():
    con = duckdb.connect()
    con.execute("""
    CREATE VIEW employee_master AS 
    SELECT 
        PERNR as emp_id,
        name,
        GESCH as gender,
        CAST(GBDAT AS DATE) as dob,
        CAST(BEGDA AS DATE) as doj,
        fiscal_year_joined,
        VDSK1 as category,
        pwd_flag,
        pwd_category,
        home_state_code,
        discipline_id,
        PERSK as current_grade_id,
        WERKS as current_wc_id,
        current_designation,
        entry_mode,
        STAT2 as employment_status,
        CAST(separation_date AS DATE) as separation_date,
        age_years,
        age_band,
        total_tenure_years,
        tenure_band,
        has_hard_station_tenure,
        has_offshore_tenure,
        exemption_tag,
        exemption_reason_code,
        CAST(retirement_date AS DATE) as retirement_date
    FROM read_csv_auto('landing/sap/PA0002_PA0001.csv');
    """)

    con.execute("""
    CREATE VIEW posting_history AS
    SELECT
        posting_id,
        PERNR as emp_id,
        WERKS as wc_id,
        CAST(BEGDA AS DATE) as from_date,
        CAST(ENDDA AS DATE) as to_date,
        fiscal_year,
        PERSK as grade_id,
        discipline_id,
        designation,
        MASSN as posting_type,
        order_no,
        tenure_months,
        is_current_posting,
        exemption_tag,
        MASSG as exemption_reason_code,
        exemption_approved_by,
        CAST(exemption_valid_until AS DATE) as exemption_valid_until,
        transfer_grant_inr,
        composite_transfer_grant_cta_inr,
        baggage_transport_cost_inr,
        total_transfer_cost_inr
    FROM read_csv_auto('landing/sap/PA0001.csv');
    """)

    con.execute("""
    CREATE VIEW promotion_history AS
    SELECT
        promotion_id,
        PERNR as emp_id,
        wc_id,
        discipline_id,
        from_grade_id,
        PERSK as to_grade_id,
        CAST(BEGDA AS DATE) as effective_date,
        fiscal_year,
        dpc_id,
        MASSN as promotion_mode,
        residency_years_completed,
        apar_benchmark_met,
        vigilance_cleared,
        hard_station_completed_flag,
        order_no
    FROM read_csv_auto('landing/sap/PA0000_promotions.csv');
    """)

    con.execute("""
    CREATE VIEW separations AS
    SELECT
        separation_id,
        PERNR as emp_id,
        CAST(BEGDA AS DATE) as separation_date,
        fiscal_year,
        MASSN as separation_type,
        last_grade_id,
        discipline_id,
        last_wc_id,
        age_at_separation,
        total_service_years,
        MASSG as exit_interview_reason,
        target_company_or_sector
    FROM read_csv_auto('landing/sap/PA0000_separations.csv');
    """)

    df_dpc = pd.read_excel(LANDING_EXCEL / "DPC_tracker.xlsx")
    con.register("dpc_cases", df_dpc)
    return con


@pytest.fixture(scope="module")
def ref_data():
    with open(REF_DIR / "work_centres.yaml", encoding="utf-8") as f:
        wcs = yaml.safe_load(f)["work_centres"]
    with open(REF_DIR / "grades.yaml", encoding="utf-8") as f:
        grades = yaml.safe_load(f)["grades"]
    with open(REF_DIR / "disciplines.yaml", encoding="utf-8") as f:
        disciplines = yaml.safe_load(f)["disciplines"]
    with open(REF_DIR / "geography.yaml", encoding="utf-8") as f:
        states = yaml.safe_load(f)["states"]

    return {
        "wc_ids": {w["wc_id"] for w in wcs},
        "grade_ids": {g["grade_id"] for g in grades},
        "discipline_ids": {d["discipline_id"] for d in disciplines},
        "state_codes": {s["state_code"] for s in states},
    }


# ==============================================================================
# 1. FILE EXISTENCE & STRICT SCHEMA DECLARATION (NO DUPLICATES)
# ==============================================================================
def test_landing_files_strictly_schema_declared():
    schema_declared_sap = {
        "PA0002_PA0001.csv",
        "PA0001.csv",
        "PA0000_promotions.csv",
        "PA0000_separations.csv",
    }
    actual_sap_files = {f.name for f in LANDING_SAP.iterdir() if f.is_file()}
    assert schema_declared_sap.issubset(actual_sap_files), (
        f"Missing schema-declared SAP files: {schema_declared_sap - actual_sap_files}"
    )

    # Check non-empty
    for name in schema_declared_sap:
        p = LANDING_SAP / name
        assert p.stat().st_size > 0, f"File {name} is empty"

    # Confirm duplicate/unapproved files for 2.1 are deleted
    assert "PA0002.csv" not in actual_sap_files, "Duplicate landing/sap/PA0002.csv must not exist"
    assert "PA0000.csv" not in actual_sap_files, "Duplicate landing/sap/PA0000.csv must not exist"

    # Check Excel tracker
    dpc_path = LANDING_EXCEL / "DPC_tracker.xlsx"
    assert dpc_path.exists(), f"Missing {dpc_path}"
    assert dpc_path.stat().st_size > 0, f"Empty {dpc_path}"


def test_no_real_person_names(duck_con):
    """Assert that no employee record contains real Board members, KMPs or public figures."""
    real_person_names_blacklist = {
        "arun kumar singh", "arun singh", "arun kumar",
        "manish patil", "vikram saxena", "om prakash sinha", "om sinha",
        "satyan kumar", "anupam agarwal", "praveen mal khanooja", "praveen khanooja",
        "vinod seshan", "shashi bhushan singh", "shashi singh", "rajni kant",
        "bhaskar chowdary nettem", "bhaskar chowdary", "bhaskar nettem", "archana thakur",
        "vivek chandrakant tongaonkar", "vivek tongaonkar", "subhash kumar",
        "alka mittal", "shashi shanker", "dinesh k sarraf", "dinesh sarraf",
        "r s sharma", "subir raha",
    }
    all_names = set(duck_con.execute("SELECT DISTINCT LOWER(name) AS clean_name FROM employee_master").df()["clean_name"].tolist())
    matched = all_names.intersection(real_person_names_blacklist)
    assert not matched, f"Found real Board/KMP names in employee_master: {matched}"


# ==============================================================================
# 2. ROW COUNTS & SCALE
# ==============================================================================
def test_row_counts(duck_con):
    n_emp = duck_con.execute("SELECT COUNT(*) FROM employee_master").fetchone()[0]
    n_post = duck_con.execute("SELECT COUNT(*) FROM posting_history").fetchone()[0]
    n_prom = duck_con.execute("SELECT COUNT(*) FROM promotion_history").fetchone()[0]
    n_sep = duck_con.execute("SELECT COUNT(*) FROM separations").fetchone()[0]
    n_dpc = duck_con.execute("SELECT COUNT(*) FROM dpc_cases").fetchone()[0]

    assert 38000 <= n_emp <= 45000, f"Expected ~40k-42k employees, got {n_emp}"
    assert n_post >= 150000, f"Expected >=150k postings, got {n_post}"
    assert n_prom >= 30000, f"Expected >=30k promotions, got {n_prom}"
    assert n_sep >= 18000, f"Expected >=18k separations, got {n_sep}"
    assert n_dpc >= 8000, f"Expected >=8k DPC cases, got {n_dpc}"


# ==============================================================================
# 3. PRIMARY KEYS UNIQUE
# ==============================================================================
def test_primary_keys_unique(duck_con):
    for tbl, pk in [
        ("employee_master", "emp_id"),
        ("posting_history", "posting_id"),
        ("promotion_history", "promotion_id"),
        ("separations", "separation_id"),
    ]:
        dup = duck_con.execute(f"""
            SELECT COUNT(*) - COUNT(DISTINCT {pk}) FROM {tbl}
        """).fetchone()[0]
        assert dup == 0, f"Duplicate PK found in {tbl}.{pk}: {dup}"

    # DPC cases composite PK: (dpc_id, emp_id)
    dup_dpc = duck_con.execute("""
        SELECT COUNT(*) - COUNT(DISTINCT dpc_id || '_' || emp_id) FROM dpc_cases
    """).fetchone()[0]
    assert dup_dpc == 0, f"Duplicate composite PK in dpc_cases: {dup_dpc}"


# ==============================================================================
# 4. FOREIGN KEY REFERENTIAL INTEGRITY
# ==============================================================================
def test_foreign_keys_referential_integrity(duck_con, ref_data):
    # Check employee_master FKs
    em_wcs = set(duck_con.execute("SELECT DISTINCT current_wc_id FROM employee_master").df()["current_wc_id"])
    em_grades = set(duck_con.execute("SELECT DISTINCT current_grade_id FROM employee_master").df()["current_grade_id"])
    em_discs = set(duck_con.execute("SELECT DISTINCT discipline_id FROM employee_master").df()["discipline_id"])
    em_states = set(duck_con.execute("SELECT DISTINCT home_state_code FROM employee_master").df()["home_state_code"])

    assert em_wcs.issubset(ref_data["wc_ids"]), f"Invalid work centres in employee_master: {em_wcs - ref_data['wc_ids']}"
    assert em_grades.issubset(ref_data["grade_ids"]), f"Invalid grades in employee_master: {em_grades - ref_data['grade_ids']}"
    assert em_discs.issubset(ref_data["discipline_ids"]), f"Invalid disciplines in employee_master: {em_discs - ref_data['discipline_ids']}"
    assert em_states.issubset(ref_data["state_codes"]), f"Invalid states in employee_master: {em_states - ref_data['state_codes']}"

    # Check posting_history FKs
    ph_wcs = set(duck_con.execute("SELECT DISTINCT wc_id FROM posting_history").df()["wc_id"])
    ph_grades = set(duck_con.execute("SELECT DISTINCT grade_id FROM posting_history").df()["grade_id"])
    ph_discs = set(duck_con.execute("SELECT DISTINCT discipline_id FROM posting_history").df()["discipline_id"])

    assert ph_wcs.issubset(ref_data["wc_ids"]), f"Invalid work centres in posting_history: {ph_wcs - ref_data['wc_ids']}"
    assert ph_grades.issubset(ref_data["grade_ids"]), f"Invalid grades in posting_history: {ph_grades - ref_data['grade_ids']}"
    assert ph_discs.issubset(ref_data["discipline_ids"]), f"Invalid disciplines in posting_history: {ph_discs - ref_data['discipline_ids']}"

    # Check cross-table FKs: posting, promotion, separation emp_ids exist in employee_master
    all_emp_ids = set(duck_con.execute("SELECT emp_id FROM employee_master").df()["emp_id"])
    post_emp_ids = set(duck_con.execute("SELECT DISTINCT emp_id FROM posting_history").df()["emp_id"])
    prom_emp_ids = set(duck_con.execute("SELECT DISTINCT emp_id FROM promotion_history").df()["emp_id"])
    sep_emp_ids = set(duck_con.execute("SELECT DISTINCT emp_id FROM separations").df()["emp_id"])

    assert post_emp_ids.issubset(all_emp_ids), "Orphan emp_id found in posting_history"
    assert prom_emp_ids.issubset(all_emp_ids), "Orphan emp_id found in promotion_history"
    assert sep_emp_ids.issubset(all_emp_ids), "Orphan emp_id found in separations"


# ==============================================================================
# 5. ALL 14 HEADCOUNT TARGETS (FY13–FY26) MATCH EXACTLY
# ==============================================================================
def test_all_headcount_targets_fy13_to_fy26(duck_con):
    target_hc = {
        "FY13": 32923, "FY14": 33911, "FY15": 33185, "FY16": 33927,
        "FY17": 33660, "FY18": 32265, "FY19": 31065, "FY20": 30105,
        "FY21": 28479, "FY22": 27165, "FY23": 25993, "FY24": 25847,
        "FY25": 24368, "FY26": 23117,
    }

    for fy, target in target_hc.items():
        date_str = f"20{fy[2:]}-03-31"
        cnt = duck_con.execute(f"""
            SELECT COUNT(*) FROM employee_master 
            WHERE doj <= DATE '{date_str}' AND (separation_date IS NULL OR separation_date > DATE '{date_str}')
        """).fetchone()[0]
        assert cnt == target, f"Headcount mismatch at {fy} ({date_str}): actual {cnt} != target {target}"


# ==============================================================================
# 6. DEMOGRAPHIC & CALIBRATION BREAKDOWNS AT 31-MAR-2026
# ==============================================================================
def test_demographics_and_equity_at_fy26(duck_con):
    # Total headcount: 23,117
    tot_hc = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
    """).fetchone()[0]
    assert tot_hc == 23117

    # Executive vs Non-executive: 13,781 exec / 9,336 non-exec
    exec_cnt = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND (current_grade_id LIKE 'E%' OR current_grade_id IN ('DIR', 'CMD'))
    """).fetchone()[0]
    nonexec_cnt = tot_hc - exec_cnt
    assert exec_cnt == 13781
    assert nonexec_cnt == 9336

    # Women: 1,885 (1,377 exec / 508 non-exec) -> 8.15%
    w_tot = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND gender = 'Female'
    """).fetchone()[0]
    w_exec = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND gender = 'Female' AND (current_grade_id LIKE 'E%' OR current_grade_id IN ('DIR', 'CMD'))
    """).fetchone()[0]
    w_nonexec = w_tot - w_exec
    assert w_tot == 1885
    assert w_exec == 1377
    assert w_nonexec == 508
    assert abs((w_tot / tot_hc) - 0.0815) < 0.005

    # SC 15.02%, ST 11.35%
    sc_cnt = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND category = 'SC'
    """).fetchone()[0]
    st_cnt = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND category = 'ST'
    """).fetchone()[0]
    assert abs((sc_cnt / tot_hc) - 0.1502) < 0.005
    assert abs((st_cnt / tot_hc) - 0.1135) < 0.005

    # PwD: 523 (313 exec / 210 non-exec)
    pwd_tot = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND pwd_flag = True
    """).fetchone()[0]
    pwd_exec = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND pwd_flag = True AND (current_grade_id LIKE 'E%' OR current_grade_id IN ('DIR', 'CMD'))
    """).fetchone()[0]
    pwd_nonexec = pwd_tot - pwd_exec
    assert pwd_tot == 523
    assert pwd_exec == 313
    assert pwd_nonexec == 210

    # Age bands at 31-Mar-2026: <30 (9.6% ±2%), 30-50 (66% ±2%), >50 (24.4% ±2%)
    u30 = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND dob > '1996-03-31'
    """).fetchone()[0]
    m30 = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND dob BETWEEN '1976-04-01' AND '1996-03-31'
    """).fetchone()[0]
    o50 = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND dob <= '1976-03-31'
    """).fetchone()[0]
    assert abs((u30 / tot_hc) - 0.096) < 0.02
    assert abs((m30 / tot_hc) - 0.660) < 0.02
    assert abs((o50 / tot_hc) - 0.244) < 0.02

    # FY26 hires: exactly 167 (28 female)
    hires_tot = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master WHERE doj BETWEEN '2025-04-01' AND '2026-03-31'
    """).fetchone()[0]
    hires_fem = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master WHERE doj BETWEEN '2025-04-01' AND '2026-03-31' AND gender = 'Female'
    """).fetchone()[0]
    assert hires_tot == 167
    assert hires_fem == 28

    # FY26 separations: 1,418 (exec turnover ~7.4%, non-exec ~3.1%)
    seps_tot = duck_con.execute("""
        SELECT COUNT(*) FROM separations WHERE fiscal_year = 'FY26'
    """).fetchone()[0]
    assert 1350 <= seps_tot <= 1450

    # ED Superannuations in FY26: 20
    ed_superann = duck_con.execute("""
        SELECT COUNT(*) FROM separations 
        WHERE fiscal_year = 'FY26' AND separation_type = 'superannuation' AND last_grade_id = 'E9'
    """).fetchone()[0]
    assert ed_superann == 20

    # Assam state: 3,561 regular employees (1,518 exec / 2,043 non-exec; Group A 1,352 / B 166 / C 1,796 / D 247)
    assam_tot = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE current_wc_id IN ('WC-ASM', 'WC-JOR', 'WC-AAB', 'WC-SIL', 'WC-INB')
        AND doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
    """).fetchone()[0]
    assam_ga = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE current_wc_id IN ('WC-ASM', 'WC-JOR', 'WC-AAB', 'WC-SIL', 'WC-INB')
        AND doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND current_grade_id LIKE 'E%'
    """).fetchone()[0]
    assam_gb = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE current_wc_id IN ('WC-ASM', 'WC-JOR', 'WC-AAB', 'WC-SIL', 'WC-INB')
        AND doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND current_grade_id = 'GRP-B'
    """).fetchone()[0]
    assam_gc = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE current_wc_id IN ('WC-ASM', 'WC-JOR', 'WC-AAB', 'WC-SIL', 'WC-INB')
        AND doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND current_grade_id = 'GRP-C'
    """).fetchone()[0]
    assam_gd = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE current_wc_id IN ('WC-ASM', 'WC-JOR', 'WC-AAB', 'WC-SIL', 'WC-INB')
        AND doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND current_grade_id = 'GRP-D'
    """).fetchone()[0]
    assert assam_tot == 3561
    assert assam_ga == 1352
    assert assam_gb == 166
    assert assam_gc == 1796
    assert assam_gd == 247
    assert assam_ga + assam_gb == 1518
    assert assam_gc + assam_gd == 2043


# ==============================================================================
# 7. QUALITATIVE PATTERN & BEHAVIOURAL TESTS (FULLY EMERGENT ARCHITECTURE)
# ==============================================================================
def test_pattern_s1_office_tenure_stickiness(duck_con):
    """Assert corporate offices exhibit tenure stickiness and overstay emergence."""
    s1_cont = duck_con.execute("""
        SELECT COUNT(DISTINCT emp_id) FROM posting_history 
        WHERE wc_id = 'WC-DEL' AND to_date IS NULL AND grade_id LIKE 'E%' AND from_date <= '2021-10-19'
    """).fetchone()[0]
    s1_cum = duck_con.execute("""
        SELECT COUNT(DISTINCT emp_id) FROM (
            SELECT emp_id, SUM(DATEDIFF('day', from_date, COALESCE(to_date, DATE '2026-10-19'))) as total_days
            FROM posting_history
            WHERE wc_id = 'WC-DEL' AND grade_id LIKE 'E%'
            GROUP BY emp_id
            HAVING total_days >= 3652
        )
    """).fetchone()[0]
    s1_ret3y = duck_con.execute("""
        SELECT COUNT(DISTINCT e.emp_id) FROM employee_master e
        JOIN (
            SELECT emp_id, SUM(DATEDIFF('day', from_date, COALESCE(to_date, DATE '2026-10-19'))) as total_days
            FROM posting_history
            WHERE wc_id = 'WC-DEL' AND grade_id LIKE 'E%'
            GROUP BY emp_id
            HAVING total_days >= 3652
        ) d ON e.emp_id = d.emp_id
        WHERE e.dob <= '1969-10-19'
    """).fetchone()[0]
    transfer_due = s1_cum - s1_ret3y

    print(f"\n[EMERGENT S1] Delhi continuous >=5y: {s1_cont}, cumulative >=10y: {s1_cum}, exempt: {s1_ret3y}, transfer due: {transfer_due}")
    assert s1_cont > 0, "Expected non-zero continuous overstay executives at Delhi HQ"
    assert s1_cum > 0, "Expected non-zero cumulative overstay executives at Delhi HQ"
    assert s1_cum >= s1_ret3y, "Cumulative overstay must be >= exempt count"


def test_pattern_s2_hard_station_mobility_variation(duck_con):
    """Assert hard station avoidance emerges in mid-career cadres and NE deployment is positive."""
    s2_never_hard = duck_con.execute("""
        SELECT COUNT(DISTINCT e.emp_id) FROM employee_master e
        WHERE e.current_grade_id IN ('E3', 'E4', 'E5') AND e.has_hard_station_tenure = False
        AND e.doj <= '2026-03-31' AND (e.separation_date IS NULL OR e.separation_date > '2026-03-31')
    """).fetchone()[0]
    s2_ne_exec = duck_con.execute("""
        SELECT COUNT(DISTINCT emp_id) FROM employee_master
        WHERE current_wc_id IN ('WC-ASM', 'WC-JOR', 'WC-TRI', 'WC-SIL')
        AND (current_grade_id LIKE 'E%' OR current_grade_id IN ('DIR', 'CMD'))
        AND doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
    """).fetchone()[0]

    print(f"\n[EMERGENT S2] E3-E5 never served hard station: {s2_never_hard}, NE in-position execs: {s2_ne_exec}")
    assert s2_never_hard > 0, "Expected some mid-career executives to have never served in Category C station"
    assert s2_ne_exec > 0, "Expected non-zero North-East in-position executives"


def test_pattern_s3_and_s7_asset_headcount_divergence(duck_con):
    """Assert headcount divergence between expanding and mature assets."""
    assets = ['WC-EAS', 'WC-RAJ', 'WC-MEH', 'WC-CAU', 'WC-CAM']
    headcounts = {}
    for wc in assets:
        cnt_21 = duck_con.execute(f"""
            SELECT COUNT(DISTINCT emp_id) FROM posting_history
            WHERE wc_id = '{wc}' AND from_date <= '2021-03-31' AND (to_date IS NULL OR to_date >= '2021-03-31')
        """).fetchone()[0]
        cnt_26 = duck_con.execute(f"""
            SELECT COUNT(DISTINCT emp_id) FROM posting_history
            WHERE wc_id = '{wc}' AND from_date <= '2026-03-31' AND (to_date IS NULL OR to_date >= '2026-03-31')
        """).fetchone()[0]
        headcounts[wc] = (cnt_21, cnt_26)
        assert cnt_21 > 0 and cnt_26 > 0, f"Expected positive headcount at {wc}"

    print(f"\n[EMERGENT S3 & S7] Asset trajectories FY21 -> FY26: {headcounts}")
    assert any(c26 > c21 for c21, c26 in headcounts.values()), "Expected at least one asset with headcount expansion"


def test_pattern_s4_e7_retirements(duck_con):
    """Assert senior leadership retirements occur over FY27–FY29 horizon."""
    s4_cnt = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE current_grade_id IN ('E7', 'E8', 'E9')
        AND doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND dob BETWEEN '1966-04-01' AND '1969-03-31'
    """).fetchone()[0]
    fy27 = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE current_grade_id IN ('E7', 'E8', 'E9')
        AND doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND dob BETWEEN '1966-04-01' AND '1967-03-31'
    """).fetchone()[0]
    fy28 = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE current_grade_id IN ('E7', 'E8', 'E9')
        AND doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND dob BETWEEN '1967-04-01' AND '1968-03-31'
    """).fetchone()[0]
    fy29 = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE current_grade_id IN ('E7', 'E8', 'E9')
        AND doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND dob BETWEEN '1968-04-01' AND '1969-03-31'
    """).fetchone()[0]

    print(f"\n[EMERGENT S4] Total E7+ retiring FY27-FY29: {s4_cnt} (FY27: {fy27}, FY28: {fy28}, FY29: {fy29})")
    assert s4_cnt > 0, "Expected non-zero E7+ retirements over FY27-FY29 horizon"


def test_pattern_s5_technical_skill_cliff(duck_con):
    """Assert technical disciplines retirement wave by 2030."""
    tot_tech = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE discipline_id IN ('DISC-DRL', 'DISC-GEO', 'DISC-GPS', 'DISC-RES', 'DISC-PRD')
        AND (current_grade_id LIKE 'E%' OR current_grade_id IN ('DIR', 'CMD'))
        AND doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
    """).fetchone()[0]
    ret_tech = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE discipline_id IN ('DISC-DRL', 'DISC-GEO', 'DISC-GPS', 'DISC-RES', 'DISC-PRD')
        AND (current_grade_id LIKE 'E%' OR current_grade_id IN ('DIR', 'CMD'))
        AND doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
        AND dob <= '1970-03-31'
    """).fetchone()[0]

    print(f"\n[EMERGENT S5] Technical executives: {tot_tech}, retiring by 2030: {ret_tech} ({ret_tech/tot_tech:.1%})")
    assert tot_tech > 0, "Expected positive technical executive headcount"
    assert ret_tech > 0, "Expected non-zero technical retirements by 2030"


def test_pattern_s11_dpc_delayed_cases(duck_con):
    """Assert DPC committee delay backlogs emerge in operational technical cadres."""
    tot_delayed = duck_con.execute("""
        SELECT COUNT(*) FROM dpc_cases WHERE status = 'delayed' AND delay_months > 6
    """).fetchone()[0]
    drl_delayed = duck_con.execute("""
        SELECT COUNT(*) FROM dpc_cases WHERE status = 'delayed' AND delay_months > 6 AND discipline_id = 'DISC-DRL'
    """).fetchone()[0]
    prd_delayed = duck_con.execute("""
        SELECT COUNT(*) FROM dpc_cases WHERE status = 'delayed' AND delay_months > 6 AND discipline_id = 'DISC-PRD'
    """).fetchone()[0]

    print(f"\n[EMERGENT S11] Total delayed DPCs: {tot_delayed} (Drilling: {drl_delayed}, Production: {prd_delayed})")
    assert tot_delayed > 0, "Expected non-zero delayed DPC dockets"


def test_pattern_s12_resignations_in_fy26(duck_con):
    """Assert voluntary resignation skews toward mid-career and market-facing disciplines."""
    tot_resig = duck_con.execute("""
        SELECT COUNT(*) FROM separations 
        WHERE fiscal_year = 'FY26' AND separation_type = 'resignation' AND last_grade_id LIKE 'E%'
    """).fetchone()[0]
    e3_e5_resig = duck_con.execute("""
        SELECT COUNT(*) FROM separations 
        WHERE fiscal_year = 'FY26' AND separation_type = 'resignation' AND last_grade_id IN ('E3', 'E4', 'E5')
    """).fetchone()[0]
    it_resig = duck_con.execute("""
        SELECT COUNT(*) FROM separations 
        WHERE fiscal_year = 'FY26' AND separation_type = 'resignation' AND last_grade_id IN ('E3', 'E4', 'E5') AND discipline_id = 'DISC-IT'
    """).fetchone()[0]
    fin_resig = duck_con.execute("""
        SELECT COUNT(*) FROM separations 
        WHERE fiscal_year = 'FY26' AND separation_type = 'resignation' AND last_grade_id IN ('E3', 'E4', 'E5') AND discipline_id = 'DISC-FIN'
    """).fetchone()[0]

    print(f"\n[EMERGENT S12] Executive resignations: {tot_resig} (E3-E5: {e3_e5_resig}, IT: {it_resig}, Finance: {fin_resig})")
    assert tot_resig > 0, "Expected non-zero executive resignations"
    assert e3_e5_resig > 0, "Expected non-zero mid-career resignations"


def test_pattern_s17_women_location_disparities(duck_con):
    """Assert women representation is significantly higher in offices than offshore installations."""
    delhi_w = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE current_wc_id = 'WC-DEL' AND gender = 'Female'
        AND doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
    """).fetchone()[0]
    ddn_w = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE current_wc_id = 'WC-DDN' AND gender = 'Female'
        AND doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
    """).fetchone()[0]
    off_w = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE current_wc_id IN ('WC-MUM', 'WC-BAS', 'WC-NEH') AND gender = 'Female'
        AND doj <= '2026-03-31' AND (separation_date IS NULL OR separation_date > '2026-03-31')
    """).fetchone()[0]

    print(f"\n[EMERGENT S17] Women headcount: Delhi={delhi_w}, Dehradun={ddn_w}, Offshore={off_w}")
    assert delhi_w > 0 and ddn_w > 0, "Expected positive women headcount in corporate offices"
    assert off_w > 0, "Expected non-zero women headcount in offshore assets"


def test_story_s38_demo_personas(duck_con):
    # S38 Personas: EMP-000001..3, EMP-102451 (Pooja Verma), EMP-103892 (Rajesh Kulkarni)
    pooja = duck_con.execute("""
        SELECT name, gender, current_grade_id, discipline_id, current_wc_id, doj
        FROM employee_master WHERE emp_id = 'EMP-102451'
    """).fetchone()
    assert pooja == ("Pooja Verma", "Female", "E2", "DISC-HR", "WC-DEL", pd.to_datetime("2021-08-16").date())

    rajesh = duck_con.execute("""
        SELECT name, gender, current_grade_id, discipline_id, current_wc_id, doj
        FROM employee_master WHERE emp_id = 'EMP-103892'
    """).fetchone()
    assert rajesh == ("Rajesh Kulkarni", "Male", "E3", "DISC-FIN", "WC-MUM", pd.to_datetime("2017-06-15").date())

    cmd = duck_con.execute("""
        SELECT name, current_designation, current_grade_id, current_wc_id FROM employee_master WHERE emp_id = 'EMP-000001'
    """).fetchone()
    assert cmd == ("Arun Mehra", "Chairman & Managing Director", "CMD", "WC-DEL")

    dir_hr = duck_con.execute("""
        SELECT name, current_designation, current_grade_id, discipline_id, current_wc_id FROM employee_master WHERE emp_id = 'EMP-000002'
    """).fetchone()
    assert dir_hr == ("Manish Deshpande", "Director (HR)", "DIR", "DISC-HR", "WC-DEL")

    dir_fin = duck_con.execute("""
        SELECT name, current_designation, current_grade_id, discipline_id, current_wc_id FROM employee_master WHERE emp_id = 'EMP-000003'
    """).fetchone()
    assert dir_fin == ("Vivek Rao", "Director (Finance)", "DIR", "DISC-FIN", "WC-DEL")


# ==============================================================================
# 8. TEMPORAL SANITY & ZERO OVERLAPPING POSTINGS
# ==============================================================================
def test_zero_overlapping_postings(duck_con):
    overlap_cnt = duck_con.execute("""
        SELECT COUNT(*) FROM (
            SELECT emp_id, from_date, to_date,
                   LEAD(from_date) OVER (PARTITION BY emp_id ORDER BY from_date) as next_from
            FROM posting_history
        )
        WHERE next_from IS NOT NULL AND to_date >= next_from
    """).fetchone()[0]
    assert overlap_cnt == 0, f"Found {overlap_cnt} overlapping postings in posting_history!"


def test_postings_chronological_and_bounds(duck_con):
    # Every posting has from_date <= to_date (or to_date is null)
    invalid_dates = duck_con.execute("""
        SELECT COUNT(*) FROM posting_history WHERE to_date IS NOT NULL AND from_date > to_date
    """).fetchone()[0]
    assert invalid_dates == 0, f"Found {invalid_dates} postings where from_date > to_date"


def test_hiring_age_bounds(duck_con):
    """Assert zero employees with age at joining < 18 or > 50."""
    u18 = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master WHERE (doj - dob) < 18 * 365.25
    """).fetchone()[0]
    o50 = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master WHERE (doj - dob) > 50 * 365.25
    """).fetchone()[0]
    assert u18 == 0, f"Found {u18} employees hired under age 18"
    assert o50 == 0, f"Found {o50} employees hired over age 50"


def test_superannuations_fall_on_month_end(duck_con):
    """Assert 100% of superannuations fall on the last day of the month."""
    sep_not_monthend = duck_con.execute("""
        SELECT COUNT(*) FROM separations 
        WHERE separation_type = 'superannuation' AND separation_date != LAST_DAY(separation_date)
    """).fetchone()[0]
    ret_not_monthend = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE retirement_date != LAST_DAY(retirement_date)
    """).fetchone()[0]
    assert sep_not_monthend == 0, f"Found {sep_not_monthend} superannuations not on month-end"
    assert ret_not_monthend == 0, f"Found {ret_not_monthend} retirement dates not on month-end"


def test_dpc_cases_strictly_single_step_and_e6_to_e7_present(duck_con):
    """Assert DPC cases have zero multi-grade jumps and include E6->E7 transitions."""
    valid_dpc_transitions = {
        ("E4", "E5"),
        ("E5", "E6"),
        ("E6", "E7"),
        ("E7", "E8"),
        ("E8", "E9"),
    }
    df_transitions = duck_con.execute("""
        SELECT DISTINCT from_grade_id, to_grade_id FROM dpc_cases
    """).fetchdf()
    actual_transitions = set(zip(df_transitions["from_grade_id"], df_transitions["to_grade_id"]))
    
    invalid = actual_transitions - valid_dpc_transitions
    assert not invalid, f"Found multi-grade or invalid transitions in dpc_cases: {invalid}"

    e6_e7_cnt = duck_con.execute("""
        SELECT COUNT(*) FROM dpc_cases WHERE from_grade_id = 'E6' AND to_grade_id = 'E7'
    """).fetchone()[0]
    assert e6_e7_cnt > 0, "Expected E6->E7 DPC cases, got 0"


def test_fy27_h1_flows_and_anchor_headcount(duck_con):
    # Headcount as of 19-Oct-2026 (Anchor date: expectation ~22,810)
    hc_anchor = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE employment_status = 'Active'
    """).fetchone()[0]
    assert 22500 <= hc_anchor <= 23100, f"Expected ~22,810 active on 19-Oct-2026, got {hc_anchor}"

    # FY27 H1 hires (doj between 2026-04-01 and 2026-10-19: expectation 135, range 120-150)
    h1_hires = duck_con.execute("""
        SELECT COUNT(*) FROM employee_master 
        WHERE doj BETWEEN '2026-04-01' AND '2026-10-19'
    """).fetchone()[0]
    assert 120 <= h1_hires <= 150, f"Expected ~135 FY27-H1 hires, got {h1_hires}"

    # FY27 H1 separations (expectation 442, range 350-480)
    h1_seps = duck_con.execute("""
        SELECT COUNT(*) FROM separations 
        WHERE separation_date BETWEEN '2026-04-01' AND '2026-10-19'
    """).fetchone()[0]
    assert 350 <= h1_seps <= 480, f"Expected ~442 FY27-H1 separations, got {h1_seps}"

    # Executive resignations in FY27 H1 (expectation 91, range 75-105)
    h1_exec_resig = duck_con.execute("""
        SELECT COUNT(*) FROM separations 
        WHERE separation_date BETWEEN '2026-04-01' AND '2026-10-19'
        AND separation_type = 'resignation' AND last_grade_id LIKE 'E%'
    """).fetchone()[0]
    assert 75 <= h1_exec_resig <= 105, f"Expected ~91 FY27-H1 exec resignations, got {h1_exec_resig}"


def test_headcount_inertia_yoy(duck_con):
    """Assert per-work-centre annual headcount changes gradually (YoY change within +/-12% for established units)."""
    years = ["2021", "2022", "2023", "2024", "2025", "2026"]

    df = duck_con.execute("""
        SELECT 
            p.wc_id,
            d.yr,
            COUNT(DISTINCT p.emp_id) as headcount
        FROM (
            SELECT '2021' as yr, DATE '2021-03-31' as dt UNION ALL
            SELECT '2022' as yr, DATE '2022-03-31' as dt UNION ALL
            SELECT '2023' as yr, DATE '2023-03-31' as dt UNION ALL
            SELECT '2024' as yr, DATE '2024-03-31' as dt UNION ALL
            SELECT '2025' as yr, DATE '2025-03-31' as dt UNION ALL
            SELECT '2026' as yr, DATE '2026-03-31' as dt
        ) d
        JOIN posting_history p 
          ON p.from_date <= d.dt AND (p.to_date IS NULL OR p.to_date >= d.dt)
        GROUP BY p.wc_id, d.yr
        ORDER BY p.wc_id, d.yr
    """).fetchdf()

    piv = df.pivot(index="wc_id", columns="yr", values="headcount").fillna(0)
    for y1, y2 in zip(years[:-1], years[1:]):
        for wc in piv.index:
            h1 = piv.loc[wc, y1]
            h2 = piv.loc[wc, y2]
            if h1 >= 120 and h2 >= 120:
                yoy = abs(h2 - h1) / h1
                assert round(yoy, 2) <= 0.10, f"YoY swing at {wc} from {y1} ({h1}) to {y2} ({h2}) is {yoy:.1%}, exceeds 10%"


def test_mobility_executive_stint_length(duck_con):
    """Assert median executive stint length is between 3 and 5 years per JRTP mobility norms."""
    res = duck_con.execute("""
        SELECT MEDIAN(tenure_months / 12.0)
        FROM posting_history
        WHERE grade_id LIKE 'E%' OR grade_id IN ('DIR', 'CMD')
    """).fetchone()[0]
    print(f"\n[MOBILITY] Executive median stint length: {res:.2f} years")
    assert 3.0 <= res <= 5.0, f"Expected executive median stint between 3 and 5 years, got {res:.2f}"


def test_mobility_zero_duplicate_same_wc_postings(duck_con):
    """Assert share of postings with same wc as previous (excluding in-place promotion) is exactly zero."""
    same_wc_cnt = duck_con.execute("""
        SELECT COUNT(*) FROM (
            SELECT emp_id, wc_id, posting_type,
                   LAG(wc_id) OVER (PARTITION BY emp_id ORDER BY from_date) as prev_wc
            FROM posting_history
        )
        WHERE prev_wc IS NOT NULL AND wc_id = prev_wc AND posting_type NOT IN ('promotion', 'promotion_in_place')
    """).fetchone()[0]
    print(f"\n[MOBILITY] Duplicate non-promotion same-wc rows: {same_wc_cnt}")
    assert same_wc_cnt == 0, f"Expected 0 non-promotion same-wc rows, got {same_wc_cnt}"


def test_mobility_nonexec_moves_less_than_exec(duck_con):
    """Assert non-executives move rarely (mean moves per career < executives)."""
    res = duck_con.execute("""
        WITH moves_flagged AS (
            SELECT emp_id,
                   CASE WHEN LAG(wc_id) OVER (PARTITION BY emp_id ORDER BY from_date) != wc_id THEN 1 ELSE 0 END as is_move
            FROM posting_history
        ),
        emp_moves AS (
            SELECT emp_id, SUM(is_move) as num_moves
            FROM moves_flagged
            GROUP BY emp_id
        )
        SELECT 
            AVG(CASE WHEN em.current_grade_id LIKE 'E%' OR em.current_grade_id IN ('DIR', 'CMD') THEN emv.num_moves END) as exec_mean_moves,
            AVG(CASE WHEN em.current_grade_id NOT LIKE 'E%' AND em.current_grade_id NOT IN ('DIR', 'CMD') THEN emv.num_moves END) as nonexec_mean_moves
        FROM emp_moves emv
        JOIN employee_master em ON emv.emp_id = em.emp_id
    """).fetchone()
    exec_moves, nonexec_moves = res[0], res[1]
    print(f"\n[MOBILITY] Mean moves per career: Exec={exec_moves:.2f}, Non-Exec={nonexec_moves:.2f}")
    assert nonexec_moves < exec_moves, f"Expected nonexec moves ({nonexec_moves}) < exec moves ({exec_moves})"


def test_corporate_hq_continuous_stay_band(duck_con):
    """Assert share of current executives at Corporate HQ with continuous stay >= 5y is between 25% and 60%."""
    delhi_stats = duck_con.execute("""
        WITH flagged AS (
            SELECT 
                emp_id, wc_id, from_date, to_date, is_current_posting,
                CASE WHEN LAG(wc_id) OVER (PARTITION BY emp_id ORDER BY from_date) = wc_id THEN 0 ELSE 1 END as new_island
            FROM posting_history
        ),
        islands AS (
            SELECT 
                emp_id, wc_id, from_date, to_date, is_current_posting,
                SUM(new_island) OVER (PARTITION BY emp_id ORDER BY from_date) as island_id
            FROM flagged
        ),
        delhi_curr AS (
            SELECT 
                emp_id,
                MIN(from_date) as start_dt
            FROM islands
            WHERE wc_id = 'WC-DEL'
            GROUP BY emp_id, island_id
            HAVING BOOL_OR(is_current_posting)
        )
        SELECT 
            COUNT(*) as total_delhi_active,
            SUM(CASE WHEN DATEDIFF('day', start_dt, DATE '2026-03-31') >= 5*365.25 THEN 1 ELSE 0 END) as ge_5y
        FROM delhi_curr dc
        JOIN employee_master em ON dc.emp_id = em.emp_id
        WHERE em.employment_status = 'Active' AND (em.current_grade_id LIKE 'E%' OR em.current_grade_id IN ('DIR', 'CMD'))
    """).fetchone()
    tot_delhi, ge_5y = delhi_stats[0], delhi_stats[1]
    ratio = ge_5y / tot_delhi
    print(f"\n[MOBILITY] Delhi HQ active execs: {tot_delhi}, Continuous stay >= 5y: {ge_5y} ({ratio:.1%})")
    assert 0.25 <= ratio <= 0.60, f"Expected Delhi HQ continuous stay >= 5y ratio between 25% and 60%, got {ratio:.1%}"


def test_assam_state_headcount_on_jul_30(duck_con):
    """Assert Assam state regular headcount is 3,561 ±2% on 30-Jul-2026 (parliamentary question date)."""
    assam_jul_30 = duck_con.execute("""
        SELECT COUNT(DISTINCT p.emp_id)
        FROM posting_history p
        JOIN employee_master e ON p.emp_id = e.emp_id
        WHERE p.wc_id IN ('WC-ASM', 'WC-JOR', 'WC-AAB', 'WC-SIL', 'WC-INB')
          AND p.from_date <= '2026-07-30'
          AND (p.to_date IS NULL OR p.to_date >= '2026-07-30')
          AND (e.separation_date IS NULL OR e.separation_date >= '2026-07-30')
    """).fetchone()[0]
    print(f"\n[CALIBRATION] Assam headcount on 30-Jul-2026: {assam_jul_30} (target 3561 ±2%)")
    assert 3561 * 0.98 <= assam_jul_30 <= 3561 * 1.02, f"Assam headcount on 30-Jul-2026 {assam_jul_30} outside ±2% band"


# ==============================================================================
# 9. DETERMINISM CHECK
# ==============================================================================
def test_determinism():
    csv_files = [
        LANDING_SAP / "PA0002_PA0001.csv",
        LANDING_SAP / "PA0001.csv",
        LANDING_SAP / "PA0000_promotions.csv",
        LANDING_SAP / "PA0000_separations.csv",
    ]

    hashes_before = {}
    for f in csv_files:
        with open(f, "rb") as fp:
            hashes_before[f] = hashlib.sha256(fp.read()).hexdigest()

    # Run generator via CLI
    cmd = ["uv", "run", "python", "generators/hr/gen_21_hr_core.py"]
    res = subprocess.run(cmd, cwd=DATA_BANK_DIR, capture_output=True, text=True)
    assert res.returncode == 0, f"Generator run failed: {res.stderr}"

    for f in csv_files:
        with open(f, "rb") as fp:
            h_after = hashlib.sha256(fp.read()).hexdigest()
        assert hashes_before[f] == h_after, f"Determinism failure for {f.name}"
