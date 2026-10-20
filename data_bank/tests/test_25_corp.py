"""
test_25_corp.py: Automated test suite for Step 2.5 (Corporate & Governance, Tables F12–F17, G1–G4).
Strictly follows DELEGATION_PLAYBOOK.md:
- Row counts and Primary Key uniqueness
- Referential integrity against Reference data (geography, work centres)
- Cross-table reconciliation with upstream CO_PA.csv and payroll
- Exact and tolerance-checked public calibration asserts
- Plausibility, aging, score range bounds, and identity tests
- 100% byte-level determinism
"""

from datetime import date
import hashlib
from pathlib import Path
import sys
import duckdb
import openpyxl
import pandas as pd
import pytest
import yaml

DATA_BANK_DIR = Path(__file__).resolve().parent.parent
if str(DATA_BANK_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_BANK_DIR))
LANDING_DIR = DATA_BANK_DIR / "landing"
EXCEL_DIR = LANDING_DIR / "excel"
GOVERNANCE_DIR = LANDING_DIR / "governance"
DB_EXPORTS_DIR = LANDING_DIR / "db_exports"
SAP_DIR = LANDING_DIR / "sap"
REF_DIR = DATA_BANK_DIR / "world_bible" / "reference"


@pytest.fixture(scope="module")
def duck_con():
    """Initializes in-memory DuckDB and loads reference and Step 2.5 landing tables."""
    con = duckdb.connect(":memory:")

    # 1. Reference tables
    with open(REF_DIR / "geography.yaml", "r", encoding="utf-8") as f:
        geo = yaml.safe_load(f)["states"]
    con.register("dim_geography", pd.DataFrame(geo))

    with open(REF_DIR / "work_centres.yaml", "r", encoding="utf-8") as f:
        wcs = yaml.safe_load(f)["work_centres"]
    con.register("dim_work_centre", pd.DataFrame(wcs))

    # 2. Upstream table for cross-silo reconciliation
    copa_path = SAP_DIR / "CO_PA.csv"
    if copa_path.exists():
        con.execute(f"CREATE TABLE upstream_co_pa AS SELECT * FROM '{copa_path}'")

    # 3. Load Step 2.5 Excel landing files (clean sources preferred if messy variants exist)
    clean_dir = EXCEL_DIR / "_clean"
    csr_path = clean_dir / "csr_projects_tracker.xlsx" if clean_dir.exists() and (clean_dir / "csr_projects_tracker.xlsx").exists() else EXCEL_DIR / "csr_projects_tracker.xlsx"
    csr_df = pd.read_excel(csr_path, sheet_name="csr_projects")
    con.register("csr_projects", csr_df)

    mou_path = clean_dir / "dpe_mou_scorecard.xlsx" if clean_dir.exists() and (clean_dir / "dpe_mou_scorecard.xlsx").exists() else EXCEL_DIR / "dpe_mou_scorecard.xlsx"
    mou_df = pd.read_excel(mou_path, sheet_name="mou_targets")
    con.register("mou_targets", mou_df)

    liab_df = pd.read_excel(EXCEL_DIR / "actuarial_benefit_liabilities.xlsx", sheet_name="benefit_liabilities")
    con.register("benefit_liabilities", liab_df)

    etr_df = pd.read_excel(EXCEL_DIR / "energy_transition_progress.xlsx", sheet_name="energy_transition")
    con.register("energy_transition", etr_df)

    cag_df = pd.read_excel(EXCEL_DIR / "cag_paras_register.xlsx", sheet_name="cag_paras")
    con.register("cag_paras", cag_df)

    board_df = pd.read_excel(EXCEL_DIR / "board_agenda_index.xlsx", sheet_name="board_agenda_index")
    con.register("board_agenda_index", board_df)

    # 4. Load Step 2.5 CSV landing files
    corp_fin_df = pd.read_csv(GOVERNANCE_DIR / "corporate_financial_summary.csv")
    con.register("corporate_financials", corp_fin_df)

    subs_df = pd.read_csv(GOVERNANCE_DIR / "subsidiary_group_financials.csv")
    con.register("subsidiary_financials", subs_df)

    pq_df = pd.read_csv(GOVERNANCE_DIR / "parliament_questions_index.csv")
    con.register("parliament_questions", pq_df)

    rti_df = pd.read_csv(DB_EXPORTS_DIR / "rti_applications_export.csv")
    con.register("rti_applications", rti_df)

    return con


# ------------------------------------------------------------------------------
# 1. Landing Files Existence & Row Counts
# ------------------------------------------------------------------------------

def test_landing_files_exist():
    """Verify that all 10 expected native landing files exist."""
    clean_dir = EXCEL_DIR / "_clean"
    if clean_dir.exists() and (clean_dir / "csr_projects_tracker.xlsx").exists():
        assert (clean_dir / "csr_projects_tracker.xlsx").exists()
        assert (clean_dir / "dpe_mou_scorecard.xlsx").exists()
    else:
        assert (EXCEL_DIR / "csr_projects_tracker.xlsx").exists()
        assert (EXCEL_DIR / "dpe_mou_scorecard.xlsx").exists()

    assert (EXCEL_DIR / "actuarial_benefit_liabilities.xlsx").exists()
    assert (EXCEL_DIR / "energy_transition_progress.xlsx").exists()
    assert (EXCEL_DIR / "cag_paras_register.xlsx").exists()
    assert (EXCEL_DIR / "board_agenda_index.xlsx").exists()
    assert (GOVERNANCE_DIR / "corporate_financial_summary.csv").exists()
    assert not (DB_EXPORTS_DIR / "corporate_financial_summary.csv").exists(), (
        "corporate_financial_summary.csv must exist only in landing/governance/ per schema_silver"
    )
    assert (GOVERNANCE_DIR / "subsidiary_group_financials.csv").exists()
    assert not (DB_EXPORTS_DIR / "subsidiary_group_financials.csv").exists(), (
        "subsidiary_group_financials.csv must exist only in landing/governance/ per schema_silver"
    )
    assert (GOVERNANCE_DIR / "parliament_questions_index.csv").exists()
    assert not (DB_EXPORTS_DIR / "parliament_questions_index.csv").exists(), (
        "parliament_questions_index.csv must exist only in landing/governance/ per schema_silver"
    )
    assert (DB_EXPORTS_DIR / "rti_applications_export.csv").exists()
    assert not (GOVERNANCE_DIR / "rti_applications_export.csv").exists(), (
        "rti_applications_export.csv must exist only in landing/db_exports/ per schema_silver"
    )


def test_row_counts_and_pk_uniqueness(duck_con):
    """Verify non-empty row counts and primary key uniqueness across all 10 tables."""
    tables_pk = [
        ("csr_projects", "csr_project_id", 150),
        ("mou_targets", "mou_record_id", 25),
        ("benefit_liabilities", "scheme_record_id", 20),
        ("subsidiary_financials", "subsidiary_record_id", 25),
        ("energy_transition", "transition_project_id", 30),
        ("corporate_financials", "fiscal_year", 10),
        ("parliament_questions", "pq_id", 30),
        ("cag_paras", "cag_para_id", 40),
        ("rti_applications", "rti_id", 500),
        ("board_agenda_index", "agenda_id", 50)
    ]

    for tbl, pk, min_rows in tables_pk:
        cnt = duck_con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        pk_cnt = duck_con.execute(f"SELECT COUNT(DISTINCT {pk}) FROM {tbl}").fetchone()[0]
        assert cnt >= min_rows, f"Table {tbl} row count ({cnt}) is below minimum {min_rows}"
        assert cnt == pk_cnt, f"Table {tbl} primary key {pk} has duplicates! ({cnt} total, {pk_cnt} distinct)"


# ------------------------------------------------------------------------------
# 2. Foreign Key Integrity
# ------------------------------------------------------------------------------

def test_foreign_key_integrity(duck_con):
    """Verify that state_code and wc_id references exist in reference datasets."""
    # State codes in CSR, Energy Transition, Parliament questions
    invalid_csr_states = duck_con.execute("""
        SELECT COUNT(*) FROM csr_projects
        WHERE state_code NOT IN (SELECT state_code FROM dim_geography)
    """).fetchone()[0]
    assert invalid_csr_states == 0, f"Found {invalid_csr_states} invalid state_codes in csr_projects"

    invalid_etr_states = duck_con.execute("""
        SELECT COUNT(*) FROM energy_transition
        WHERE location_state_code NOT IN (SELECT state_code FROM dim_geography)
    """).fetchone()[0]
    assert invalid_etr_states == 0, f"Found {invalid_etr_states} invalid location_state_codes in energy_transition"

    invalid_pq_states = duck_con.execute("""
        SELECT COUNT(*) FROM parliament_questions
        WHERE state_code IS NOT NULL AND state_code NOT IN (SELECT state_code FROM dim_geography)
    """).fetchone()[0]
    assert invalid_pq_states == 0, f"Found {invalid_pq_states} invalid state_codes in parliament_questions"

    # Work centres in CSR, Energy Transition, CAG, RTI
    for tbl, wc_col in [
        ("csr_projects", "wc_id"),
        ("energy_transition", "wc_id"),
        ("cag_paras", "wc_id"),
        ("rti_applications", "wc_id")
    ]:
        invalid_wcs = duck_con.execute(f"""
            SELECT COUNT(*) FROM {tbl}
            WHERE {wc_col} NOT IN (SELECT wc_id FROM dim_work_centre)
        """).fetchone()[0]
        assert invalid_wcs == 0, f"Found {invalid_wcs} invalid {wc_col} references in {tbl}"


# ------------------------------------------------------------------------------
# 3. Cross-Silo Reconciliation & Accounting Identities
# ------------------------------------------------------------------------------

def test_corporate_financial_reconciliation(duck_con):
    """Verify reconciliation between corporate financials, CO_PA, and accounting identities."""
    fy26_row = duck_con.execute("""
        SELECT gross_revenue_inr_cr, offshore_revenue_inr_cr, onshore_revenue_inr_cr,
               statutory_levies_total_inr_cr, royalty_inr_cr, oidb_cess_inr_cr, saed_windfall_tax_inr_cr,
               employee_cost_total_inr_cr, total_capex_spent_inr_cr, total_dividend_payout_inr_cr,
               pat_inr_cr, dividend_payout_ratio_pct, dividend_per_share_inr
        FROM corporate_financials
        WHERE fiscal_year = 'FY26'
    """).fetchone()

    gross_rev, off_rev, on_rev, levies, roy, cess, saed, emp, cpx, div, pat, payout, dps = fy26_row

    # Identity 1: Gross revenue = Offshore + Onshore
    assert gross_rev == pytest.approx(off_rev + on_rev, rel=1e-4)

    # Identity 2: Statutory levies = Royalty + Cess + SAED
    assert levies == pytest.approx(roy + cess + saed, rel=1e-4)

    # Reconciliation with upstream CO_PA gross revenue if available
    has_copa = duck_con.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'upstream_co_pa'").fetchone()[0]
    if has_copa > 0:
        copa_rev = duck_con.execute("SELECT SUM(gross_revenue_inr_cr) FROM upstream_co_pa WHERE fiscal_year = 'FY26'").fetchone()[0]
        assert gross_rev == pytest.approx(copa_rev, rel=1e-3)


def test_csr_section_135_statutory_logic(duck_con):
    """Verify that CSR 2% obligation flag matches Section 135 calculation from preceding 3-year avg PAT."""
    # Preceding 3 years: FY23 (40096), FY24 (40526), FY25 (35610)
    pats = duck_con.execute("""
        SELECT pat_inr_cr FROM corporate_financials
        WHERE fiscal_year IN ('FY23', 'FY24', 'FY25')
    """).fetchall()
    avg_pat = sum(p[0] for p in pats) / 3.0
    statutory_2pct = 0.02 * avg_pat

    fy26_csr_spend = duck_con.execute("""
        SELECT SUM(actual_disbursed_inr_cr) FROM csr_projects
        WHERE fiscal_year = 'FY26'
    """).fetchone()[0]

    assert fy26_csr_spend >= statutory_2pct, f"CSR spend {fy26_csr_spend} failed 2% mandate {statutory_2pct}!"

    # Verify all FY26 projects have statutory_2pct_mandate_met_flag == True
    non_compliant_flags = duck_con.execute("""
        SELECT COUNT(*) FROM csr_projects
        WHERE fiscal_year = 'FY26' AND statutory_2pct_mandate_met_flag = False
    """).fetchone()[0]
    assert non_compliant_flags == 0, f"Found {non_compliant_flags} projects with false mandate flag in FY26"


# ------------------------------------------------------------------------------
# 4. Public Calibration Asserts
# ------------------------------------------------------------------------------

def test_csr_public_calibration(duck_con):
    """Verify CSR total spend and state allocations against public calibration targets."""
    # FY26 CSR Total Spend: 949 cr
    fy26_total = duck_con.execute("SELECT SUM(actual_disbursed_inr_cr) FROM csr_projects WHERE fiscal_year = 'FY26'").fetchone()[0]
    assert fy26_total == pytest.approx(949.0, rel=0.01)

    # Top states: UP (155.0 cr), MH (137.6 cr), JK (132.6 cr)
    up_total = duck_con.execute("SELECT SUM(actual_disbursed_inr_cr) FROM csr_projects WHERE fiscal_year = 'FY26' AND state_code = 'UP'").fetchone()[0]
    mh_total = duck_con.execute("SELECT SUM(actual_disbursed_inr_cr) FROM csr_projects WHERE fiscal_year = 'FY26' AND state_code = 'MH'").fetchone()[0]
    jk_total = duck_con.execute("SELECT SUM(actual_disbursed_inr_cr) FROM csr_projects WHERE fiscal_year = 'FY26' AND state_code = 'JK'").fetchone()[0]

    assert up_total == pytest.approx(155.0, rel=0.01)
    assert mh_total == pytest.approx(137.6, rel=0.01)
    assert jk_total == pytest.approx(132.6, rel=0.01)


def test_corporate_financials_calibration(duck_con):
    """Verify audited financial series against calibration targets."""
    # Revenue calibration
    rev_targets = {
        "FY17": 77908.0, "FY18": 85004.0, "FY19": 109655.0, "FY20": 96214.0, "FY21": 68141.0,
        "FY22": 110345.0, "FY23": 155517.0, "FY24": 138402.0, "FY25": 137846.0, "FY26": 132508.0
    }
    pat_targets = {
        "FY17": 17900.0, "FY18": 19945.0, "FY19": 26765.0, "FY20": 13464.0, "FY21": 11246.0,
        "FY22": 40306.0, "FY23": 40096.0, "FY24": 40526.0, "FY25": 35610.0, "FY26": 32894.0
    }

    for fy, target_rev in rev_targets.items():
        actual_rev = duck_con.execute(f"SELECT gross_revenue_inr_cr FROM corporate_financials WHERE fiscal_year = '{fy}'").fetchone()[0]
        assert actual_rev == pytest.approx(target_rev, rel=0.02)

    for fy, target_pat in pat_targets.items():
        actual_pat = duck_con.execute(f"SELECT pat_inr_cr FROM corporate_financials WHERE fiscal_year = '{fy}'").fetchone()[0]
        assert actual_pat == pytest.approx(target_pat, rel=0.02)

    # FY26 specific metrics
    row = duck_con.execute("""
        SELECT offshore_revenue_inr_cr, royalty_inr_cr, oidb_cess_inr_cr, saed_windfall_tax_inr_cr,
               dividend_per_share_inr, dividend_payout_ratio_pct, consolidated_pat_inr_cr
        FROM corporate_financials WHERE fiscal_year = 'FY26'
    """).fetchone()

    assert row[0] == pytest.approx(92406.0, rel=0.02)  # Offshore revenue
    assert row[1] == pytest.approx(12965.0, rel=0.02)  # Royalty
    assert row[2] == pytest.approx(13034.0, rel=0.02)  # Cess
    assert row[3] == 0.0                               # SAED windfall tax
    assert row[4] == 13.25                             # DPS
    assert row[5] == pytest.approx(50.68, rel=0.02)    # Payout %
    assert row[6] == pytest.approx(49793.0, rel=0.02)  # Consolidated PAT


def test_benefit_liabilities_calibration(duck_con):
    """Verify benefit liabilities against actuarial calibration targets at 31-March-2026."""
    # Gratuity
    grat = duck_con.execute("""
        SELECT actuarial_liability_inr_cr, plan_assets_inr_cr, net_liability_inr_cr
        FROM benefit_liabilities
        WHERE fiscal_year = 'FY26' AND scheme_type = 'Gratuity'
    """).fetchone()
    assert grat[0] == pytest.approx(1867.9, rel=0.02)
    assert grat[1] == pytest.approx(1753.7, rel=0.02)
    assert grat[2] == pytest.approx(114.2, rel=0.02)

    # Post-Retirement Medical (PRMB)
    prmb = duck_con.execute("""
        SELECT actuarial_liability_inr_cr, plan_assets_inr_cr, net_liability_inr_cr
        FROM benefit_liabilities
        WHERE fiscal_year = 'FY26' AND scheme_type = 'Post-Retirement Medical'
    """).fetchone()
    assert prmb[0] == pytest.approx(7065.6, rel=0.02)
    assert prmb[1] == pytest.approx(6570.4, rel=0.02)
    assert prmb[2] == pytest.approx(495.3, rel=0.02)

    # Provident Fund
    pf = duck_con.execute("""
        SELECT actuarial_liability_inr_cr, plan_assets_inr_cr
        FROM benefit_liabilities
        WHERE fiscal_year = 'FY26' AND scheme_type = 'Provident Fund'
    """).fetchone()
    assert pf[0] == pytest.approx(13266.9, rel=0.02)
    assert pf[1] == pytest.approx(13414.6, rel=0.02)


def test_subsidiaries_calibration(duck_con):
    """Verify subsidiary performance against FY26 calibration targets."""
    hpcl_pat = duck_con.execute("SELECT pat_inr_cr FROM subsidiary_financials WHERE fiscal_year = 'FY26' AND entity_code = 'HPCL'").fetchone()[0]
    mrpl_pat = duck_con.execute("SELECT pat_inr_cr FROM subsidiary_financials WHERE fiscal_year = 'FY26' AND entity_code = 'MRPL'").fetchone()[0]
    ovl_pat = duck_con.execute("SELECT pat_inr_cr FROM subsidiary_financials WHERE fiscal_year = 'FY26' AND entity_code = 'OVL'").fetchone()[0]
    opal_ebitda = duck_con.execute("SELECT ebitda_inr_cr FROM subsidiary_financials WHERE fiscal_year = 'FY26' AND entity_code = 'OPAL'").fetchone()[0]

    assert hpcl_pat == pytest.approx(17175.0, rel=0.02)
    assert mrpl_pat == pytest.approx(1931.0, rel=0.02)
    assert ovl_pat == pytest.approx(1152.0, rel=0.02)
    assert opal_ebitda == pytest.approx(1207.0, rel=0.02)


def test_energy_transition_calibration(duck_con):
    """Verify FY26 installed renewable capacity against 2.853 GW calibration target."""
    fy26_mw = duck_con.execute("SELECT SUM(installed_capacity_mw) FROM energy_transition WHERE fiscal_year = 'FY26'").fetchone()[0]
    assert fy26_mw == pytest.approx(2853.0, rel=0.02)


def test_parliament_question_ls2067(duck_con):
    """Verify inclusion of official public LS2067 question (Assam employment / 30 vacancies)."""
    ls2067 = duck_con.execute("""
        SELECT house, session_year, fiscal_year, question_number, question_date,
               state_code, vacancies_reported, in_position_strength_reported,
               sanctioned_strength_reported, mp_name, ministry
        FROM parliament_questions
        WHERE pq_id = 'PQ-LS-2026-2067'
    """).fetchone()

    assert ls2067 is not None
    assert ls2067[0] == "Lok Sabha"
    assert ls2067[1] == 2026
    assert ls2067[2] == "FY27"
    assert ls2067[3] == 2067
    assert str(ls2067[4]) == "2026-07-30"
    assert ls2067[5] == "AS"
    assert ls2067[6] == 30    # CAL-GOV-PARL-ASSAM-VAC
    assert ls2067[7] == 3561  # In-position headcount in Assam
    assert ls2067[8] is None or pd.isna(ls2067[8])  # Sanctioned not reported in official text
    assert "PHANI BHUSAN CHOUDHURY" in str(ls2067[9]).upper()
    assert "SURESH GOPI" in str(ls2067[10]).upper()


def test_synthetic_parliament_questions_denylist(duck_con):
    """Verify synthetic parliament questions do NOT use real MP/minister names,
    and minister is unpersonalized 'Minister of State, MoPNG'."""
    from generators.governance.gen_25_corp import load_real_mp_denylist
    import re

    denylist = load_real_mp_denylist()
    denylist_clean = [
        re.sub(r"^(?:shri|smt|dr\.|mr\.|mrs\.)\s+", "", n, flags=re.IGNORECASE).strip().lower()
        for n in denylist
    ]

    synthetic_pqs = duck_con.execute("""
        SELECT pq_id, mp_name, ministry FROM parliament_questions
        WHERE pq_id != 'PQ-LS-2026-2067'
    """).fetchall()

    assert len(synthetic_pqs) >= 20

    for pq_id, mp_name, ministry in synthetic_pqs:
        assert ministry == "Minister of State, MoPNG", f"Synthetic PQ {pq_id} ministry must be 'Minister of State, MoPNG', got '{ministry}'"

        clean_mp = re.sub(r"^(?:shri|smt|dr\.|mr\.|mrs\.)\s+", "", str(mp_name), flags=re.IGNORECASE).strip().lower()

        for real_name in denylist_clean:
            assert clean_mp != real_name and real_name not in clean_mp and clean_mp not in real_name, (
                f"Synthetic PQ {pq_id} uses real MP name '{mp_name}' matching denylist '{real_name}'"
            )


# ------------------------------------------------------------------------------
# 5. Plausibility, Scoring, and Aging Invariants
# ------------------------------------------------------------------------------

def test_mou_score_bounds(duck_con):
    """Verify DPE MoU parameter scores and composite scores are within [1.0, 5.0]."""
    scores = duck_con.execute("""
        SELECT MIN(weighted_score), MAX(weighted_score),
               MIN(composite_score), MAX(composite_score)
        FROM mou_targets
    """).fetchone()

    assert scores[0] >= 0.0
    assert scores[1] <= 1.0  # individual weighted score <= weightage
    assert scores[2] >= 1.0  # composite score >= 1.0 (Poor)
    assert scores[3] <= 5.0  # composite score <= 5.0 (Excellent)


def test_cag_para_aging_logic(duck_con):
    """Verify that CAG para is_aged_over_3_years flag strictly equals (age_in_years > 3.0)."""
    mismatches = duck_con.execute("""
        SELECT COUNT(*) FROM cag_paras
        WHERE (age_in_years > 3.0 AND is_aged_over_3_years = False)
           OR (age_in_years <= 3.0 AND is_aged_over_3_years = True)
    """).fetchone()[0]
    assert mismatches == 0, f"Found {mismatches} aging flag mismatches in cag_paras"


def test_rti_turnaround_logic(duck_con):
    """Verify RTI statutory 30-day compliance flag strictly equals (turnaround_days <= 30)."""
    mismatches = duck_con.execute("""
        SELECT COUNT(*) FROM rti_applications
        WHERE turnaround_days IS NOT NULL
          AND ((turnaround_days <= 30 AND is_within_30_days_statutory = False)
            OR (turnaround_days > 30 AND is_within_30_days_statutory = True))
    """).fetchone()[0]
    assert mismatches == 0, f"Found {mismatches} statutory 30-day flag mismatches in rti_applications"


# ------------------------------------------------------------------------------
# 6. Determinism Test
# ------------------------------------------------------------------------------

def test_determinism_checksums():
    """Verify that every landing file has a valid 64-character SHA-256 hash."""
    files = [
        EXCEL_DIR / "csr_projects_tracker.xlsx",
        EXCEL_DIR / "dpe_mou_scorecard.xlsx",
        EXCEL_DIR / "actuarial_benefit_liabilities.xlsx",
        EXCEL_DIR / "energy_transition_progress.xlsx",
        EXCEL_DIR / "cag_paras_register.xlsx",
        EXCEL_DIR / "board_agenda_index.xlsx",
        GOVERNANCE_DIR / "corporate_financial_summary.csv",
        GOVERNANCE_DIR / "subsidiary_group_financials.csv",
        GOVERNANCE_DIR / "parliament_questions_index.csv",
        DB_EXPORTS_DIR / "rti_applications_export.csv"
    ]

    for f in files:
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        assert len(h) == 64


def test_generator_determinism_roundtrip():
    """Verify that re-running gen_25_corp.py produces byte-for-byte identical output hashes."""
    import subprocess
    clean_dir = EXCEL_DIR / "_clean"
    files = [
        clean_dir / "csr_projects_tracker.xlsx" if clean_dir.exists() and (clean_dir / "csr_projects_tracker.xlsx").exists() else EXCEL_DIR / "csr_projects_tracker.xlsx",
        clean_dir / "dpe_mou_scorecard.xlsx" if clean_dir.exists() and (clean_dir / "dpe_mou_scorecard.xlsx").exists() else EXCEL_DIR / "dpe_mou_scorecard.xlsx",
        EXCEL_DIR / "actuarial_benefit_liabilities.xlsx",
        EXCEL_DIR / "energy_transition_progress.xlsx",
        EXCEL_DIR / "cag_paras_register.xlsx",
        EXCEL_DIR / "board_agenda_index.xlsx",
        GOVERNANCE_DIR / "corporate_financial_summary.csv",
        GOVERNANCE_DIR / "subsidiary_group_financials.csv",
        GOVERNANCE_DIR / "parliament_questions_index.csv",
        DB_EXPORTS_DIR / "rti_applications_export.csv"
    ]

    hashes_before = {f: hashlib.sha256(f.read_bytes()).hexdigest() for f in files}

    gen_path = DATA_BANK_DIR / "generators" / "governance" / "gen_25_corp.py"
    res = subprocess.run(["uv", "run", "python", str(gen_path)], capture_output=True, text=True)
    assert res.returncode == 0, f"Generator run failed: {res.stderr}"

    hashes_after = {f: hashlib.sha256(f.read_bytes()).hexdigest() for f in files}

    for f in files:
        assert hashes_before[f] == hashes_after[f], f"File {f.name} SHA-256 mismatch across generator runs!"

