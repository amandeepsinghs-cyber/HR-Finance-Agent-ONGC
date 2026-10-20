"""test_gap_sprint.py: Comprehensive validation suite for Gap-Closure Sprint additions.

Validates the 4 new tables:
1. env_incidents  (landing/db_exports/env_incident_log.csv)
2. posh_cases      (landing/excel/posh_register.xlsx)
3. apprentices     (landing/sap/apprentice_ledger.csv)
4. po_channel      (landing/sap/EKKO_channel.csv)

Enforces:
- PK uniqueness & non-null integrity
- FK validity to reference (work centres, fields, icc_committees) and upstream landing (EKKO_EKPO)
- Temporal sanity across the FY22 -> Sep-2026 window
- Hard calibration: FY26 apprentices count == 1,550 (+-0)
- Plausibility bounds (incident rates, POSH 90-day enquiry norm, GeM shares)
- Proposed schema addendum completeness (world_bible_proposals/schema_silver_addendum_gaps.yaml)
- RNG isolation: SHA-256 of every pre-existing landing file is unchanged!
"""

import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import yaml

DATA_BANK_DIR = Path(__file__).resolve().parent.parent
REF_DIR = DATA_BANK_DIR / "world_bible" / "reference"
PROPOSALS_DIR = DATA_BANK_DIR / "world_bible_proposals"
LANDING_DIR = DATA_BANK_DIR / "landing"
LANDING_DB = LANDING_DIR / "db_exports"
LANDING_EXCEL = LANDING_DIR / "excel"
LANDING_SAP = LANDING_DIR / "sap"
BASELINE_MANIFEST = DATA_BANK_DIR / "tests" / "landing_baseline_manifest.sha256"


# ------------------------------------------------------------------------------
# 1. FILE EXISTENCE & PROPOSAL CHECKS
# ------------------------------------------------------------------------------
def test_files_exist():
    """Verify that all 4 landing files and the proposed schema addendum exist."""
    assert (LANDING_DB / "env_incident_log.csv").exists(), "Missing env_incident_log.csv"
    assert (LANDING_EXCEL / "posh_register.xlsx").exists(), "Missing posh_register.xlsx"
    assert (LANDING_SAP / "apprentice_ledger.csv").exists(), "Missing apprentice_ledger.csv"
    assert (LANDING_SAP / "EKKO_channel.csv").exists(), "Missing EKKO_channel.csv"

    schema_file = PROPOSALS_DIR / "schema_silver_addendum_gaps.yaml"
    assert schema_file.exists(), "Missing schema_silver_addendum_gaps.yaml"
    with open(schema_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    tables = [t["table_name"] for t in data.get("tables", [])]
    expected_tables = {"env_incidents", "posh_cases", "apprentices", "po_channel"}
    assert expected_tables.issubset(set(tables)), f"Proposed schema missing tables: {expected_tables - set(tables)}"


# ------------------------------------------------------------------------------
# 2. ENVIRONMENTAL INCIDENTS TESTS
# ------------------------------------------------------------------------------
def test_env_incidents():
    """Validate PK, FK, accepted values, and plausibility for env_incidents."""
    df = pd.read_csv(LANDING_DB / "env_incident_log.csv")
    assert len(df) > 0, "env_incident_log.csv is empty"

    # PK uniqueness
    assert df["incident_id"].nunique() == len(df), "incident_id is not unique"
    assert df["incident_id"].str.startswith("ENV-").all(), "incident_id does not follow ENV-##### format"

    # FK validation
    with open(REF_DIR / "work_centres.yaml", "r", encoding="utf-8") as f:
        valid_wcs = {w["wc_id"] for w in yaml.safe_load(f)["work_centres"]}
    with open(REF_DIR / "fields.yaml", "r", encoding="utf-8") as f:
        valid_flds = {f["field_id"] for f in yaml.safe_load(f)["fields"]}

    assert set(df["wc_id"]).issubset(valid_wcs), "Invalid wc_id in env_incidents"
    field_ids = set(df["field_id"].dropna()) - {""}
    assert field_ids.issubset(valid_flds), "Invalid field_id in env_incidents"

    # Accepted values
    valid_types = {
        "oil_spill",
        "gas_leak",
        "well_control_blowout",
        "effluent_discharge_exceedance",
        "flaring_exceedance",
    }
    assert set(df["incident_type"]).issubset(valid_types), "Unexpected incident_type"

    valid_severities = {"Tier_1", "Tier_2", "Tier_3"}
    assert set(df["severity"]).issubset(valid_severities), "Unexpected severity tier"

    valid_regulators = {"SPCB", "PNGRB", "DGMS", "OISD"}
    assert set(df["regulator"]).issubset(valid_regulators), "Unexpected regulator"

    valid_units = {"bbl", "m3"}
    assert set(df["volume_unit"]).issubset(valid_units), "Unexpected volume_unit"

    valid_statuses = {"closed", "settled", "remediated", "under_investigation"}
    assert set(df["status"]).issubset(valid_statuses), "Unexpected status"

    # Temporal sanity
    assert (df["date"] >= "2021-04-01").all() and (df["date"] <= "2026-09-30").all(), "Incident date out of window"
    assert set(df["fiscal_year"]).issubset({"FY22", "FY23", "FY24", "FY25", "FY26", "FY27"})

    # Plausibility bounds
    assert (df["volume_released"] > 0).all(), "volume_released must be strictly positive"
    penalty_rows = df[df["penalty_inr_lakh"].notna()]
    assert (penalty_rows["penalty_inr_lakh"] > 0).all(), "penalty_inr_lakh must be strictly positive when present"
    assert penalty_rows["notice_issued"].all(), "Penalty levied without notice_issued flag"


# ------------------------------------------------------------------------------
# 3. POSH REGISTER TESTS
# ------------------------------------------------------------------------------
def test_posh_cases():
    """Validate PK, FK, ageing, and annual case counts for posh_cases."""
    df = pd.read_excel(LANDING_EXCEL / "posh_register.xlsx", sheet_name="posh_cases")
    assert len(df) > 0, "posh_register.xlsx has 0 rows"

    # PK uniqueness
    assert df["case_id"].nunique() == len(df), "case_id is not unique"
    assert df["case_id"].str.startswith("POSH-").all(), "case_id format invalid"

    # FK validation
    with open(REF_DIR / "work_centres.yaml", "r", encoding="utf-8") as f:
        valid_wcs = {w["wc_id"] for w in yaml.safe_load(f)["work_centres"]}
    icc_df = pd.read_excel(LANDING_EXCEL / "icc_committees.xlsx")
    valid_comms = set(icc_df["committee_id"])

    assert set(df["wc_id"]).issubset(valid_wcs), "Invalid wc_id in posh_cases"
    assert set(df["committee_id"]).issubset(valid_comms), "Invalid committee_id in posh_cases"

    # Plausible annual counts for 23k PSU (single digits to low tens per year)
    fy_counts = df["fiscal_year"].value_counts().to_dict()
    for fy, cnt in fy_counts.items():
        assert 1 <= cnt <= 25, f"POSH count {cnt} in {fy} is not plausible for 23k PSU"

    # Accepted values
    valid_cadres = {"executive", "non_executive", "contract_worker"}
    assert set(df["complainant_cadre"]).issubset(valid_cadres), "Invalid complainant_cadre"

    valid_grade_bands = {"E1-E3", "E4-E5", "E6-E7", "E8-E9", "S-Level", "W-Level"}
    assert set(df["respondent_grade_band"]).issubset(valid_grade_bands), "Invalid respondent_grade_band"

    # Ageing & inquiry days (POSH Act 90-day inquiry norm)
    assert (df["inquiry_days"] >= 0).all(), "inquiry_days must be non-negative"
    disposed = df[df["status"] != "under_inquiry"]
    on_time_share = (disposed["inquiry_days"] <= 90).mean()
    assert on_time_share >= 0.70, f"Expected most inquiries <= 90 days, got {on_time_share:.1%}"
    assert (disposed["inquiry_days"] > 90).any(), "Expected at least a few delayed inquiries (> 90 days)"

    # Temporal sanity
    assert (df["date_received"] >= "2021-04-01").all() and (df["date_received"] <= "2026-09-30").all()


# ------------------------------------------------------------------------------
# 4. APPRENTICES TESTS & HARD CALIBRATION
# ------------------------------------------------------------------------------
def test_apprentices_calibration():
    """Validate apprentices ledger and strictly enforce FY26 = 1,550 (+-0)."""
    df = pd.read_csv(LANDING_SAP / "apprentice_ledger.csv")
    assert len(df) > 0, "apprentice_ledger.csv is empty"

    # PK uniqueness
    assert df["apprentice_id"].nunique() == len(df), "apprentice_id is not unique"
    assert df["apprentice_id"].str.startswith("APP-").all(), "apprentice_id format invalid"

    # FK validation
    with open(REF_DIR / "work_centres.yaml", "r", encoding="utf-8") as f:
        valid_wcs = {w["wc_id"] for w in yaml.safe_load(f)["work_centres"]}
    assert set(df["wc_id"]).issubset(valid_wcs), "Invalid wc_id in apprentices"

    # HARD CALIBRATION: FY26 engaged count == 1,550 (+-0)
    fy26_count_by_col = len(df[df["fiscal_year"] == "FY26"])
    assert fy26_count_by_col == 1550, f"Apprentices FY26 count by column is {fy26_count_by_col}, expected exactly 1550"

    fy26_count_by_dates = len(df[(df["start_date"] >= "2025-04-01") & (df["start_date"] <= "2026-03-31")])
    assert fy26_count_by_dates == 1550, f"Apprentices FY26 count by date range is {fy26_count_by_dates}, expected exactly 1550"

    # Accepted values
    assert set(df["trade_category"]).issubset({"technical", "non_technical"})
    assert set(df["status"]).issubset({"completed", "active", "resigned", "terminated"})
    assert set(df["category"]).issubset({"Gen", "SC", "ST", "OBC", "EWS", "PwD"})
    assert set(df["gender"]).issubset({"Male", "Female"})

    # Plausibility
    assert (df["stipend_inr_month"] >= 8000).all(), "stipend_inr_month below statutory minimum"
    assert (df["end_date"] > df["start_date"]).all(), "end_date must be after start_date"


# ------------------------------------------------------------------------------
# 5. GEM PROCUREMENT CHANNEL (EKKO_channel) TESTS
# ------------------------------------------------------------------------------
def test_po_channel():
    """Validate 1:1 join to EKKO_EKPO.csv and GeM procurement channel attributes."""
    ekko_df = pd.read_csv(LANDING_SAP / "EKKO_EKPO.csv", usecols=["po_line_id", "original_po_value_inr", "fiscal_year"])
    chan_df = pd.read_csv(LANDING_SAP / "EKKO_channel.csv")

    assert len(chan_df) == len(ekko_df), f"po_channel count {len(chan_df)} != EKKO_EKPO count {len(ekko_df)}"

    # PK uniqueness & 1:1 match
    assert chan_df["po_line_id"].nunique() == len(chan_df), "po_line_id is not unique in po_channel"
    assert set(chan_df["po_line_id"]) == set(ekko_df["po_line_id"]), "po_line_id set does not match EKKO_EKPO"

    # Accepted values
    valid_channels = {
        "GeM",
        "e-Procurement/SRM",
        "Limited tender",
        "Single/Proprietary",
        "Nomination",
    }
    assert set(chan_df["procurement_channel"]).issubset(valid_channels), "Invalid procurement_channel"

    valid_mse_cats = {"none", "SC", "ST", "women"}
    assert set(chan_df["mse_vendor_social_category"]).issubset(valid_mse_cats), "Invalid mse_vendor_social_category"

    # GeM order ID consistency
    gem_rows = chan_df[chan_df["procurement_channel"] == "GeM"]
    non_gem_rows = chan_df[chan_df["procurement_channel"] != "GeM"]

    assert gem_rows["gem_order_id"].notna().all(), "GeM rows must have non-null gem_order_id"
    assert (gem_rows["gem_order_id"].str.startswith("GEM/")).all(), "gem_order_id must start with GEM/"
    assert (non_gem_rows["gem_order_id"].isna() | (non_gem_rows["gem_order_id"] == "")).all(), "Non-GeM rows must have null/empty gem_order_id"

    # Vendor MSE consistency
    with open(REF_DIR / "vendors.yaml", "r", encoding="utf-8") as f:
        vendor_mse_map = {v["vendor_id"]: v.get("mse_flag", False) for v in yaml.safe_load(f)["vendors"]}
    po_vendor_df = pd.read_csv(LANDING_SAP / "EKKO_EKPO.csv", usecols=["po_line_id", "vendor_id"])
    merged = chan_df.merge(po_vendor_df, on="po_line_id")
    merged["is_mse"] = merged["vendor_id"].map(vendor_mse_map)

    non_mse_orders = merged[~merged["is_mse"]]
    assert (non_mse_orders["mse_vendor_social_category"] == "none").all(), "Non-MSE vendor cannot have affirmative action category"

    # Plausible GeM spend share in FY26
    merged_val = merged.merge(ekko_df[["po_line_id", "original_po_value_inr", "fiscal_year"]], on="po_line_id")
    fy26_data = merged_val[merged_val["fiscal_year"] == "FY26"]
    gem_val = fy26_data[fy26_data["procurement_channel"] == "GeM"]["original_po_value_inr"].sum()
    tot_val = fy26_data["original_po_value_inr"].sum()
    gem_share = gem_val / tot_val
    assert 0.03 <= gem_share <= 0.35, f"GeM share of PO value in FY26 ({gem_share:.1%}) outside plausible bounds [3%, 35%]"


# ------------------------------------------------------------------------------
# 6. RNG ISOLATION HASH TEST
# ------------------------------------------------------------------------------
def test_rng_isolation_existing_landing_unchanged():
    """Verify that every pre-existing landing file remains 100% byte-identical."""
    assert BASELINE_MANIFEST.exists(), f"Missing baseline manifest: {BASELINE_MANIFEST}"

    with open(BASELINE_MANIFEST, "r", encoding="utf-8") as f:
        lines = f.readlines()

    discrepancies = []
    checked_count = 0
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        exp_hash, rel_path = parts
        file_path = DATA_BANK_DIR / rel_path

        assert file_path.exists(), f"Pre-existing landing file was deleted: {rel_path}"
        cur_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if cur_hash != exp_hash:
            discrepancies.append((rel_path, exp_hash, cur_hash))
        checked_count += 1

    assert not discrepancies, f"RNG ISOLATION VIOLATION: {len(discrepancies)} pre-existing files modified! First 3: {discrepancies[:3]}"
    assert checked_count == 1526, f"Expected 1526 checked baseline files, got {checked_count}"


# ------------------------------------------------------------------------------
# 7. DETERMINISM TEST (RUN TWICE -> IDENTICAL SHA-256)
# ------------------------------------------------------------------------------
def test_determinism(tmp_path):
    """Verify that running the gap sprint generator produces identical SHA-256 outputs."""
    import subprocess
    import sys

    gen_script = DATA_BANK_DIR / "generators" / "gaps" / "gen_gap_sprint.py"

    # Record current hashes of the 4 generated files
    target_files = [
        LANDING_DB / "env_incident_log.csv",
        LANDING_EXCEL / "posh_register.xlsx",
        LANDING_SAP / "apprentice_ledger.csv",
        LANDING_SAP / "EKKO_channel.csv",
    ]
    initial_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in target_files}

    # Re-run the generator
    res = subprocess.run(["uv", "run", "python", str(gen_script)], cwd=str(DATA_BANK_DIR), capture_output=True, text=True)
    assert res.returncode == 0, f"Generator re-run failed: {res.stderr}"

    # Verify hashes are identical
    second_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in target_files}
    for fname in initial_hashes:
        assert initial_hashes[fname] == second_hashes[fname], f"Non-deterministic generation for {fname}"

