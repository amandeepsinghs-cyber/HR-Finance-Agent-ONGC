#!/usr/bin/env python3
"""gen_gap_sprint.py: Gap-Closure Sprint Generator (CMD Stress Test Additions).

Fully Emergent, Blind, and Non-Disruptive Implementation (DELEGATION_PLAYBOOK.md § HARD RULES):
- ZERO entity-ID-keyed logic: rates driven strictly by reference attribute classes
  (facility type, terrain onshore/offshore, field maturity, water cut class, discipline intensity).
- ZERO story numbers from world_bible/story_register.yaml.
- ZERO entity name branching or string literals in comparisons.
- ZERO string-wrapped numbers or single-row plugs.
- Calibrations (e.g. FY26 apprentices = 1,550) achieved via global scalars and
  Hamilton-Hare largest remainder allocation across attribute classes.
- RNG ISOLATION: dedicated seeded numpy Generator (SEED = 20261019 + 101) so all
  pre-existing landing files remain byte-identical.

Outputs strictly 4 new landing tables:
1. env_incidents  -> landing/db_exports/env_incident_log.csv
2. posh_cases      -> landing/excel/posh_register.xlsx
3. apprentices     -> landing/sap/apprentice_ledger.csv
4. po_channel      -> landing/sap/EKKO_channel.csv
"""

import io
import re
import zipfile
from datetime import date, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

# ==============================================================================
# 0. CONSTANTS, RNG ISOLATION & ATTRIBUTE CLASS PARAMETERS (PARAMS)
# ==============================================================================
# RNG ISOLATION: Dedicated seeded generator for the gap-closure sprint
SEED_BASE = 20261019
RNG_OFFSET = 101
rng = np.random.default_rng(SEED_BASE + RNG_OFFSET)

DATA_BANK_DIR = Path(__file__).resolve().parent.parent.parent
WORLD_BIBLE_DIR = DATA_BANK_DIR / "world_bible"
REF_DIR = WORLD_BIBLE_DIR / "reference"
LANDING_DIR = DATA_BANK_DIR / "landing"
LANDING_DB = LANDING_DIR / "db_exports"
LANDING_EXCEL = LANDING_DIR / "excel"
LANDING_SAP = LANDING_DIR / "sap"

LANDING_DB.mkdir(parents=True, exist_ok=True)
LANDING_EXCEL.mkdir(parents=True, exist_ok=True)
LANDING_SAP.mkdir(parents=True, exist_ok=True)

PARAMS = {
    # --------------------------------------------------------------------------
    # 1. Environmental & Process-Safety Incidents
    # --------------------------------------------------------------------------
    "env_field_base_rate": 0.08,
    "env_plant_base_rate": 0.05,
    "env_basin_base_rate": 0.02,
    "env_maturity_mult": {
        "mature": 1.40,
        "growth": 0.90,
        "frontier": 1.10,
    },
    "env_terrain_mult": {
        "offshore": 1.25,
        "onshore": 1.00,
        "corporate": 0.00,
    },
    "env_water_cut_high_threshold": 70.0,
    "env_water_cut_high_mult": 1.35,
    "env_type_weights_offshore": {
        "oil_spill": 0.28,
        "gas_leak": 0.35,
        "well_control_blowout": 0.05,
        "effluent_discharge_exceedance": 0.14,
        "flaring_exceedance": 0.18,
    },
    "env_type_weights_onshore": {
        "oil_spill": 0.24,
        "gas_leak": 0.18,
        "well_control_blowout": 0.02,
        "effluent_discharge_exceedance": 0.38,
        "flaring_exceedance": 0.18,
    },
    "env_severity_levels": ["Tier_1", "Tier_2", "Tier_3"],
    "env_severity_weights": [0.10, 0.28, 0.62],
    "env_notice_probs": {
        "Tier_1": 0.85,
        "Tier_2": 0.50,
        "Tier_3": 0.15,
    },
    "env_penalty_prob_on_notice": 0.60,
    "env_penalty_ranges": {
        "Tier_1": (24.0, 96.0),
        "Tier_2": (12.0, 36.0),
        "Tier_3": (3.0, 9.0),
    },
    "env_root_causes": [
        "pipeline_corrosion",
        "equipment_failure",
        "human_error_procedural",
        "subsurface_well_integrity",
        "process_upset_flaring",
        "adverse_weather_metocean",
    ],

    # --------------------------------------------------------------------------
    # 2. POSH Complaints Register
    # --------------------------------------------------------------------------
    "posh_annual_counts": {
        "FY22": 8,
        "FY23": 10,
        "FY24": 12,
        "FY25": 10,
        "FY26": 12,
        "FY27": 5,
    },
    "posh_wc_type_weights": {
        "office": 1.5,
        "institute": 1.25,
        "asset": 0.85,
        "plant": 0.7,
        "basin": 0.5,
    },
    "posh_complainant_cadres": ["executive", "non_executive", "contract_worker"],
    "posh_complainant_weights": [0.55, 0.35, 0.10],
    "posh_respondent_grade_bands": ["E1-E3", "E4-E5", "E6-E7", "E8-E9", "S-Level", "W-Level"],
    "posh_respondent_weights": [0.25, 0.40, 0.20, 0.05, 0.05, 0.05],
    "posh_outcome_categories": [
        "substantiated_disciplinary_action",
        "substantiated_warning_counselling",
        "unsubstantiated",
        "conciliated",
        "withdrawn",
    ],
    "posh_outcome_weights": [0.28, 0.27, 0.25, 0.15, 0.05],
    "posh_on_time_share": 0.85,
    "posh_inquiry_days_on_time_range": (36, 88),
    "posh_inquiry_days_delayed_range": (94, 135),

    # --------------------------------------------------------------------------
    # 3. Apprentices Ledger (NAPS)
    # --------------------------------------------------------------------------
    # FY26 calibrated strictly to the public figure 1,550 (AR26 p.117 / FACTS)
    "apprentice_fy_targets": {
        "FY22": 1150,
        "FY23": 1250,
        "FY24": 1380,
        "FY25": 1475,
        "FY26": 1550,
        "FY27": 780,
    },
    "apprentice_intensity_by_wc_type": {
        "asset": 1.0,
        "plant": 1.0,
        "basin": 0.7,
        "institute": 0.4,
        "office": 0.2,
    },
    "apprentice_technical_trades": [
        "Electrician",
        "Fitter",
        "Mechanic_Diesel",
        "Welder",
        "Instrument_Mechanic",
        "Electronics_Mechanic",
        "Laboratory_Assistant_Chemical_Plant",
        "Machinist",
        "Draughtsman_Mechanical",
        "Surveyor",
    ],
    "apprentice_non_technical_trades": [
        "Secretarial_Assistant",
        "Accountant",
        "Store_Keeper",
        "Executive_HR",
        "Computer_Operator_and_Programming_Assistant_COPA",
    ],
    "apprentice_social_categories": ["Gen", "OBC", "SC", "EWS", "ST", "PwD"],
    "apprentice_social_weights": [0.365, 0.270, 0.150, 0.100, 0.075, 0.040],
    "apprentice_gender_options": ["Male", "Female"],
    "apprentice_gender_weights": [0.82, 0.18],
    "apprentice_stipends": {
        "technical": [9000, 10500],
        "non_technical": [9000, 10500, 12000],
    },

    # --------------------------------------------------------------------------
    # 4. GeM Procurement Channel (EKKO_channel)
    # --------------------------------------------------------------------------
    "gem_cat_base_prob": {
        "Central IT & ERP Services": 0.55,
        "Civil Infrastructure & Road Construction": 0.35,
        "Chemicals & Demulsifiers": 0.28,
        "Tubulars, Casing & Wellheads": 0.15,
        "Workover Rigless Services": 0.10,
        "Technical Service Provider (TSP)": 0.08,
        "Aviation & Helicopter Charter": 0.02,
        "Offshore Supply Vessels (OSV)": 0.02,
        "Charter Hire Drilling Rigs": 0.01,
        "Offshore Subsea EPC & Pipe-laying": 0.01,
    },
    "gem_val_mult": {
        "under_25L": 1.40,
        "25L_to_50L": 1.25,
        "50L_to_1Cr": 1.00,
        "1Cr_to_5Cr": 0.60,
        "above_5Cr": 0.20,
    },
    "gem_fy_mult": {
        "FY22": 0.70,
        "FY23": 0.85,
        "FY24": 1.00,
        "FY25": 1.15,
        "FY26": 1.30,
        "FY27": 1.35,
    },
    "non_gem_channels": [
        "e-Procurement/SRM",
        "Limited tender",
        "Single/Proprietary",
        "Nomination",
    ],
    "non_gem_weights": [0.72, 0.16, 0.08, 0.04],
    "mse_social_categories": ["none", "women", "SC", "ST"],
    "mse_social_weights": [0.72, 0.12, 0.10, 0.06],
}


# ==============================================================================
# 1. GENERATE ENVIRONMENTAL & PROCESS-SAFETY INCIDENTS
# ==============================================================================
def generate_env_incidents() -> pd.DataFrame:
    """Generate environmental and process safety incidents for FY22 to Sep-2026."""
    print("Generating 1) Environmental & process-safety incidents (env_incident_log.csv)...")

    # Load reference fields and work centres
    with open(REF_DIR / "fields.yaml", "r", encoding="utf-8") as f:
        fields_data = yaml.safe_load(f)["fields"]
    with open(REF_DIR / "work_centres.yaml", "r", encoding="utf-8") as f:
        wcs_data = yaml.safe_load(f)["work_centres"]

    # Load production monthly to calculate field average water cut
    prod_path = LANDING_DB / "production_monthly.csv"
    water_cut_map = {}
    if prod_path.exists():
        prod_df = pd.read_csv(prod_path, usecols=["field_id", "water_cut_pct"])
        water_cut_map = prod_df.groupby("field_id")["water_cut_pct"].mean().to_dict()

    # Time series of months from 2021-04 to 2026-09 (66 months)
    start_dt = date(2021, 4, 1)
    end_dt = date(2026, 9, 30)

    # Generate list of month endpoints
    curr = start_dt
    months = []
    while curr <= end_dt:
        m_str = curr.strftime("%Y-%m")
        # Determine fiscal year
        cal_year = curr.year
        cal_month = curr.month
        fy_year = cal_year + 1 if cal_month >= 4 else cal_year
        fy_str = f"FY{str(fy_year)[2:]}"
        # Days in month
        if cal_month in (1, 3, 5, 7, 8, 10, 12):
            days_in_m = 31
        elif cal_month in (4, 6, 9, 11):
            days_in_m = 30
        else:
            days_in_m = 29 if (cal_year % 4 == 0 and (cal_year % 100 != 0 or cal_year % 400 == 0)) else 28
        months.append((m_str, fy_str, cal_year, cal_month, days_in_m))
        # Advance to next month
        if cal_month == 12:
            curr = date(cal_year + 1, 1, 1)
        else:
            curr = date(cal_year, cal_month + 1, 1)

    records = []
    incident_counter = 1

    # Loop over facilities and months
    # 1. Producing fields
    for fld in fields_data:
        fld_id = fld["field_id"]
        wc_id = fld["asset_wc_id"]
        terrain = fld.get("onshore_offshore", "onshore")
        maturity = fld.get("maturity", "mature")
        avg_wc = water_cut_map.get(fld_id, 50.0)

        # Base rate and multipliers from PARAMS
        base_rate = PARAMS["env_field_base_rate"]
        mat_mult = PARAMS["env_maturity_mult"].get(maturity, 1.0)
        ter_mult = PARAMS["env_terrain_mult"].get(terrain, 1.0)
        wc_mult = PARAMS["env_water_cut_high_mult"] if avg_wc > PARAMS["env_water_cut_high_threshold"] else 1.0

        monthly_lambda = base_rate * mat_mult * ter_mult * wc_mult

        for m_str, fy_str, c_yr, c_mo, days_in_m in months:
            k = rng.poisson(monthly_lambda)
            for _ in range(k):
                inc_id = f"ENV-{incident_counter:05d}"
                incident_counter += 1

                day = int(rng.integers(1, days_in_m + 1))
                inc_date = f"{c_yr:04d}-{c_mo:02d}-{day:02d}"

                # Incident type
                if terrain == "offshore":
                    types = list(PARAMS["env_type_weights_offshore"].keys())
                    p_types = list(PARAMS["env_type_weights_offshore"].values())
                else:
                    types = list(PARAMS["env_type_weights_onshore"].keys())
                    p_types = list(PARAMS["env_type_weights_onshore"].values())
                inc_type = rng.choice(types, p=p_types)

                # Severity
                severity = rng.choice(
                    PARAMS["env_severity_levels"],
                    p=PARAMS["env_severity_weights"],
                )

                # Volume and unit
                if inc_type == "oil_spill":
                    vol_unit = "bbl"
                    if severity == "Tier_1":
                        vol = round(float(rng.uniform(60.0, 250.0)), 2)
                    elif severity == "Tier_2":
                        vol = round(float(rng.uniform(12.0, 45.0)), 2)
                    else:
                        vol = round(float(rng.uniform(0.5, 8.0)), 2)
                elif inc_type == "well_control_blowout":
                    vol_unit = "bbl"
                    if severity == "Tier_1":
                        vol = round(float(rng.uniform(120.0, 450.0)), 2)
                    elif severity == "Tier_2":
                        vol = round(float(rng.uniform(25.0, 90.0)), 2)
                    else:
                        vol = round(float(rng.uniform(6.0, 18.0)), 2)
                elif inc_type == "gas_leak":
                    vol_unit = "m3"
                    if severity == "Tier_1":
                        vol = round(float(rng.uniform(6000.0, 35000.0)), 1)
                    elif severity == "Tier_2":
                        vol = round(float(rng.uniform(600.0, 4500.0)), 1)
                    else:
                        vol = round(float(rng.uniform(60.0, 450.0)), 1)
                elif inc_type == "effluent_discharge_exceedance":
                    vol_unit = "m3"
                    if severity == "Tier_1":
                        vol = round(float(rng.uniform(120.0, 800.0)), 1)
                    elif severity == "Tier_2":
                        vol = round(float(rng.uniform(25.0, 90.0)), 1)
                    else:
                        vol = round(float(rng.uniform(6.0, 18.0)), 1)
                else:  # flaring_exceedance
                    vol_unit = "m3"
                    if severity == "Tier_1":
                        vol = round(float(rng.uniform(25000.0, 85000.0)), 1)
                    elif severity == "Tier_2":
                        vol = round(float(rng.uniform(6000.0, 18000.0)), 1)
                    else:
                        vol = round(float(rng.uniform(800.0, 4500.0)), 1)

                # Regulator
                if inc_type == "well_control_blowout":
                    regulator = "DGMS"
                elif terrain == "offshore":
                    regulator = "OISD"
                elif inc_type in ("effluent_discharge_exceedance", "flaring_exceedance"):
                    regulator = "SPCB"
                elif inc_type == "gas_leak":
                    regulator = "PNGRB"
                else:
                    regulator = "SPCB"

                # Notice issued and penalty
                p_notice = PARAMS["env_notice_probs"].get(severity, 0.2)
                notice_issued = bool(rng.random() < p_notice)

                penalty_lakh = None
                if notice_issued and rng.random() < PARAMS["env_penalty_prob_on_notice"]:
                    p_min, p_max = PARAMS["env_penalty_ranges"][severity]
                    penalty_lakh = round(float(rng.uniform(p_min, p_max)), 2)

                # Status
                if inc_date >= "2026-07-01":
                    status = "under_investigation" if rng.random() < 0.50 else "remediated"
                else:
                    status = "closed" if rng.random() < 0.75 else "settled"

                # Root cause
                rc = rng.choice(PARAMS["env_root_causes"])

                records.append({
                    "incident_id": inc_id,
                    "date": inc_date,
                    "fiscal_year": fy_str,
                    "wc_id": wc_id,
                    "field_id": fld_id,
                    "incident_type": inc_type,
                    "severity": severity,
                    "volume_released": vol,
                    "volume_unit": vol_unit,
                    "regulator": regulator,
                    "notice_issued": notice_issued,
                    "penalty_inr_lakh": penalty_lakh,
                    "status": status,
                    "root_cause_category": rc,
                })

    # 2. Dedicated plants and basins (without specific single field_id)
    facility_wcs = [w for w in wcs_data if w.get("type") in ("plant", "basin")]
    for fac in facility_wcs:
        wc_id = fac["wc_id"]
        wc_type = fac.get("type")
        terrain = fac.get("onshore_offshore", "onshore")

        base_rate = PARAMS["env_plant_base_rate"] if wc_type == "plant" else PARAMS["env_basin_base_rate"]
        ter_mult = PARAMS["env_terrain_mult"].get(terrain, 1.0)
        monthly_lambda = base_rate * ter_mult

        for m_str, fy_str, c_yr, c_mo, days_in_m in months:
            k = rng.poisson(monthly_lambda)
            for _ in range(k):
                inc_id = f"ENV-{incident_counter:05d}"
                incident_counter += 1

                day = int(rng.integers(1, days_in_m + 1))
                inc_date = f"{c_yr:04d}-{c_mo:02d}-{day:02d}"

                if wc_type == "plant":
                    types = ["gas_leak", "effluent_discharge_exceedance", "flaring_exceedance"]
                    p_types = [0.45, 0.30, 0.25]
                else:
                    types = ["oil_spill", "gas_leak", "well_control_blowout"]
                    p_types = [0.35, 0.40, 0.25]
                inc_type = rng.choice(types, p=p_types)

                severity = rng.choice(
                    PARAMS["env_severity_levels"],
                    p=PARAMS["env_severity_weights"],
                )

                if inc_type == "oil_spill":
                    vol_unit = "bbl"
                    vol = round(float(rng.uniform(1.0, 50.0)), 2)
                elif inc_type == "well_control_blowout":
                    vol_unit = "bbl"
                    vol = round(float(rng.uniform(10.0, 100.0)), 2)
                else:
                    vol_unit = "m3"
                    vol = round(float(rng.uniform(50.0, 5000.0)), 1)

                if inc_type == "well_control_blowout":
                    regulator = "DGMS"
                elif terrain == "offshore":
                    regulator = "OISD"
                elif inc_type in ("effluent_discharge_exceedance", "flaring_exceedance"):
                    regulator = "SPCB"
                else:
                    regulator = "PNGRB" if wc_type == "plant" else "SPCB"

                p_notice = PARAMS["env_notice_probs"].get(severity, 0.2)
                notice_issued = bool(rng.random() < p_notice)

                penalty_lakh = None
                if notice_issued and rng.random() < PARAMS["env_penalty_prob_on_notice"]:
                    p_min, p_max = PARAMS["env_penalty_ranges"][severity]
                    penalty_lakh = round(float(rng.uniform(p_min, p_max)), 2)

                if inc_date >= "2026-07-01":
                    status = "under_investigation" if rng.random() < 0.50 else "remediated"
                else:
                    status = "closed" if rng.random() < 0.75 else "settled"

                rc = rng.choice(PARAMS["env_root_causes"])

                records.append({
                    "incident_id": inc_id,
                    "date": inc_date,
                    "fiscal_year": fy_str,
                    "wc_id": wc_id,
                    "field_id": "",  # Nullable for plants/basins
                    "incident_type": inc_type,
                    "severity": severity,
                    "volume_released": vol,
                    "volume_unit": vol_unit,
                    "regulator": regulator,
                    "notice_issued": notice_issued,
                    "penalty_inr_lakh": penalty_lakh,
                    "status": status,
                    "root_cause_category": rc,
                })

    df = pd.DataFrame(records)
    df.sort_values(by=["date", "incident_id"], inplace=True)
    out_csv = LANDING_DB / "env_incident_log.csv"
    df.to_csv(out_csv, index=False)
    print(f"-> Wrote {len(df)} records to {out_csv}")
    return df


def normalize_xlsx_timestamps(path: Path):
    """Normalize zip header dates and docProps/core.xml modified timestamp for byte determinism."""
    zin = zipfile.ZipFile(path, 'r')
    buf = io.BytesIO()
    zout = zipfile.ZipFile(buf, 'w')
    for item in zin.infolist():
        item.date_time = (2026, 10, 19, 0, 0, 0)
        data = zin.read(item.filename)
        if item.filename == 'docProps/core.xml':
            data = re.sub(
                rb'(<dcterms:created[^>]*>)[^<]+(</dcterms:created>)',
                rb'\g<1>2026-10-19T00:00:00Z\g<2>',
                data
            )
            data = re.sub(
                rb'(<dcterms:modified[^>]*>)[^<]+(</dcterms:modified>)',
                rb'\g<1>2026-10-19T00:00:00Z\g<2>',
                data
            )
        zout.writestr(item, data)
    zout.close()
    zin.close()
    path.write_bytes(buf.getvalue())


# ==============================================================================
# 2. GENERATE POSH COMPLAINTS REGISTER
# ==============================================================================
def generate_posh_cases() -> pd.DataFrame:
    """Generate POSH complaints register for FY22 to Sep-2026."""
    print("Generating 2) POSH complaints register (posh_register.xlsx)...")

    # Load work centres and icc_committees
    with open(REF_DIR / "work_centres.yaml", "r", encoding="utf-8") as f:
        wcs_data = yaml.safe_load(f)["work_centres"]

    icc_df = pd.read_excel(LANDING_EXCEL / "icc_committees.xlsx")
    icc_map = dict(zip(icc_df["wc_id"], icc_df["committee_id"]))

    # Estimate headcount weights for work centres
    hc_path = LANDING_SAP / "headcount_monthly_snapshot.csv"
    wc_hc = {}
    if hc_path.exists():
        hc_df = pd.read_csv(hc_path, usecols=["wc_id", "headcount", "month"])
        latest_m = hc_df["month"].max()
        wc_hc = hc_df[hc_df["month"] == latest_m].groupby("wc_id")["headcount"].sum().to_dict()

    # Calculate selection probability per work centre
    wc_weights = []
    wc_list = []
    for w in wcs_data:
        w_id = w["wc_id"]
        w_type = w.get("type", "asset")
        hc = wc_hc.get(w_id, 150)
        t_weight = PARAMS["posh_wc_type_weights"].get(w_type, 1.0)
        wc_list.append(w_id)
        wc_weights.append(hc * t_weight)
    wc_weights = np.array(wc_weights, dtype=float)
    wc_weights /= np.sum(wc_weights)

    # Date ranges per fiscal year
    fy_date_bounds = {
        "FY22": (date(2021, 4, 1), date(2022, 3, 31)),
        "FY23": (date(2022, 4, 1), date(2023, 3, 31)),
        "FY24": (date(2023, 4, 1), date(2024, 3, 31)),
        "FY25": (date(2024, 4, 1), date(2025, 3, 31)),
        "FY26": (date(2025, 4, 1), date(2026, 3, 31)),
        "FY27": (date(2026, 4, 1), date(2026, 9, 30)),
    }

    anchor_date = date(2026, 10, 19)
    records = []
    case_counter = 1

    for fy, target_count in PARAMS["posh_annual_counts"].items():
        dt_start, dt_end = fy_date_bounds[fy]
        span_days = (dt_end - dt_start).days

        # Draw work centres for this year's cases
        chosen_wcs = rng.choice(wc_list, size=target_count, p=wc_weights)

        for w_id in chosen_wcs:
            cid = f"POSH-{case_counter:04d}"
            case_counter += 1

            # Date received within the fiscal year
            d_offset = int(rng.integers(0, span_days + 1))
            rec_dt = dt_start + timedelta(days=d_offset)
            rec_str = rec_dt.strftime("%Y-%m-%d")

            # Committee FK
            comm_id = icc_map.get(w_id, "ICC-001")

            # Cadre and grade band
            cadre = rng.choice(
                PARAMS["posh_complainant_cadres"],
                p=PARAMS["posh_complainant_weights"],
            )
            resp_band = rng.choice(
                PARAMS["posh_respondent_grade_bands"],
                p=PARAMS["posh_respondent_weights"],
            )

            # Ageing & inquiry process (POSH Act 90-day norm)
            age_days = (anchor_date - rec_dt).days

            if age_days < 90:
                # Still within statutory inquiry window
                status = "under_inquiry"
                inquiry_days = age_days
                outcome = "pending_inquiry"
                disclosed = False
            else:
                # Completed inquiry
                is_on_time = rng.random() < PARAMS["posh_on_time_share"]
                if is_on_time:
                    d_min, d_max = PARAMS["posh_inquiry_days_on_time_range"]
                    inquiry_days = int(rng.integers(d_min, d_max + 1))
                else:
                    d_min, d_max = PARAMS["posh_inquiry_days_delayed_range"]
                    inquiry_days = int(rng.integers(d_min, d_max + 1))

                outcome = rng.choice(
                    PARAMS["posh_outcome_categories"],
                    p=PARAMS["posh_outcome_weights"],
                )
                if outcome == "withdrawn":
                    status = "withdrawn"
                elif outcome == "conciliated":
                    status = "conciliated"
                else:
                    status = "disposed"

                # Annual report disclosure (closed FYs are disclosed)
                disclosed = (fy != "FY27")

            records.append({
                "case_id": cid,
                "wc_id": w_id,
                "date_received": rec_str,
                "fiscal_year": fy,
                "complainant_cadre": cadre,
                "respondent_grade_band": resp_band,
                "committee_id": comm_id,
                "status": status,
                "inquiry_days": inquiry_days,
                "outcome_category": outcome,
                "annual_report_disclosed": disclosed,
            })

    df = pd.DataFrame(records)
    df.sort_values(by=["date_received", "case_id"], inplace=True)
    out_xlsx = LANDING_EXCEL / "posh_register.xlsx"
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="posh_cases", index=False)
    normalize_xlsx_timestamps(out_xlsx)
    print(f"-> Wrote {len(df)} records to {out_xlsx}")
    return df


# ==============================================================================
# 3. GENERATE APPRENTICES LEDGER (NAPS)
# ==============================================================================
def generate_apprentices() -> pd.DataFrame:
    """Generate apprentices ledger calibrated to public figure 1,550 in FY26."""
    print("Generating 3) Apprentices ledger (apprentice_ledger.csv)...")

    # Load work centres
    with open(REF_DIR / "work_centres.yaml", "r", encoding="utf-8") as f:
        wcs_data = yaml.safe_load(f)["work_centres"]

    # Load work centre headcounts
    hc_path = LANDING_SAP / "headcount_monthly_snapshot.csv"
    wc_hc = {}
    if hc_path.exists():
        hc_df = pd.read_csv(hc_path, usecols=["wc_id", "headcount", "month"])
        latest_m = hc_df["month"].max()
        wc_hc = hc_df[hc_df["month"] == latest_m].groupby("wc_id")["headcount"].sum().to_dict()

    # Compute allocation weights: headcount * technical intensity
    wc_list = []
    wc_weights = []
    wc_types = {}
    for w in wcs_data:
        w_id = w["wc_id"]
        w_type = w.get("type", "asset")
        wc_types[w_id] = w_type
        hc = wc_hc.get(w_id, 200)
        intensity = PARAMS["apprentice_intensity_by_wc_type"].get(w_type, 0.5)
        wc_list.append(w_id)
        wc_weights.append(hc * intensity)

    wc_weights = np.array(wc_weights, dtype=float)
    norm_weights = wc_weights / np.sum(wc_weights)

    fy_date_bounds = {
        "FY22": (date(2021, 4, 1), date(2022, 3, 31)),
        "FY23": (date(2022, 4, 1), date(2023, 3, 31)),
        "FY24": (date(2023, 4, 1), date(2024, 3, 31)),
        "FY25": (date(2024, 4, 1), date(2025, 3, 31)),
        "FY26": (date(2025, 4, 1), date(2026, 3, 31)),
        "FY27": (date(2026, 4, 1), date(2026, 9, 30)),
    }

    anchor_date = date(2026, 10, 19)
    records = []
    app_counter = 1

    for fy, target in PARAMS["apprentice_fy_targets"].items():
        dt_start, dt_end = fy_date_bounds[fy]
        span_days = (dt_end - dt_start).days

        # Largest Remainder (Hamilton-Hare) allocation across work centres
        exact_shares = target * norm_weights
        base_alloc = np.floor(exact_shares).astype(int)
        rem = target - int(np.sum(base_alloc))
        frac = exact_shares - base_alloc
        top_rem_idx = np.argsort(-frac)[:rem]
        base_alloc[top_rem_idx] += 1
        assert int(np.sum(base_alloc)) == target, f"Mismatch in allocation for {fy}"

        for w_idx, w_id in enumerate(wc_list):
            count_for_wc = base_alloc[w_idx]
            w_type = wc_types[w_id]

            # Technical trade ratio by work centre type
            tech_prob = 0.82 if w_type in ("asset", "plant", "basin") else 0.28

            for _ in range(count_for_wc):
                aid = f"APP-{app_counter:06d}"
                app_counter += 1

                # Start and end date (1-year duration)
                d_offset = int(rng.integers(0, span_days + 1))
                s_dt = dt_start + timedelta(days=d_offset)
                e_dt = s_dt + timedelta(days=365)

                is_tech = rng.random() < tech_prob
                if is_tech:
                    t_cat = "technical"
                    trade = rng.choice(PARAMS["apprentice_technical_trades"])
                else:
                    t_cat = "non_technical"
                    trade = rng.choice(PARAMS["apprentice_non_technical_trades"])

                # Stipend
                stipend = int(rng.choice(PARAMS["apprentice_stipends"][t_cat]))

                # Social category and gender
                cat = rng.choice(
                    PARAMS["apprentice_social_categories"],
                    p=PARAMS["apprentice_social_weights"],
                )
                gender = rng.choice(
                    PARAMS["apprentice_gender_options"],
                    p=PARAMS["apprentice_gender_weights"],
                )

                # Contract status
                if e_dt <= anchor_date:
                    status = rng.choice(["completed", "resigned", "terminated"], p=[0.94, 0.04, 0.02])
                else:
                    status = "active"

                records.append({
                    "apprentice_id": aid,
                    "trade": trade,
                    "trade_category": t_cat,
                    "wc_id": w_id,
                    "start_date": s_dt.strftime("%Y-%m-%d"),
                    "end_date": e_dt.strftime("%Y-%m-%d"),
                    "stipend_inr_month": stipend,
                    "status": status,
                    "category": cat,
                    "gender": gender,
                    "fiscal_year": fy,
                })

    df = pd.DataFrame(records)
    df.sort_values(by=["start_date", "apprentice_id"], inplace=True)
    out_csv = LANDING_SAP / "apprentice_ledger.csv"
    df.to_csv(out_csv, index=False)
    print(f"-> Wrote {len(df)} records to {out_csv}")
    return df


# ==============================================================================
# 4. GENERATE GEM PROCUREMENT CHANNEL (EKKO_channel)
# ==============================================================================
def generate_po_channel() -> pd.DataFrame:
    """Generate GeM procurement channel table keyed to EKKO_EKPO.csv."""
    print("Generating 4) GeM procurement channel (EKKO_channel.csv)...")

    ekko_path = LANDING_SAP / "EKKO_EKPO.csv"
    if not ekko_path.exists():
        raise FileNotFoundError(f"Missing required upstream landing file: {ekko_path}")

    po_df = pd.read_csv(
        ekko_path,
        usecols=["po_line_id", "po_date", "fiscal_year", "vendor_id", "service_contract_category", "original_po_value_inr"],
    )

    # Load vendor reference for MSE flag
    with open(REF_DIR / "vendors.yaml", "r", encoding="utf-8") as f:
        vendors_data = yaml.safe_load(f)["vendors"]
    vendor_mse_map = {v["vendor_id"]: v.get("mse_flag", False) for v in vendors_data}

    records = []

    for _, row in po_df.iterrows():
        p_id = row["po_line_id"]
        v_id = row["vendor_id"]
        cat = row["service_contract_category"]
        val = row["original_po_value_inr"]
        fy = row["fiscal_year"]
        po_yr = str(row["po_date"])[:4]

        # Value band classification
        if val <= 2500000:
            val_band = "under_25L"
        elif val <= 5000000:
            val_band = "25L_to_50L"
        elif val <= 10000000:
            val_band = "50L_to_1Cr"
        elif val <= 50000000:
            val_band = "1Cr_to_5Cr"
        else:
            val_band = "above_5Cr"

        base_p = PARAMS["gem_cat_base_prob"].get(cat, 0.05)
        v_mult = PARAMS["gem_val_mult"].get(val_band, 1.0)
        fy_mult = PARAMS["gem_fy_mult"].get(fy, 1.0)

        # Clamped probability of routing via GeM
        p_gem = min(0.85, max(0.005, base_p * v_mult * fy_mult))

        if rng.random() < p_gem:
            channel = "GeM"
            ord_num = int(rng.integers(1000000, 9999999))
            gem_id = f"GEM/{po_yr}/B/{ord_num}"
        else:
            channel = rng.choice(
                PARAMS["non_gem_channels"],
                p=PARAMS["non_gem_weights"],
            )
            gem_id = ""

        # MSE Affirmative Action Sub-category
        is_mse = vendor_mse_map.get(v_id, False)
        if not is_mse:
            mse_soc = "none"
        else:
            mse_soc = rng.choice(
                PARAMS["mse_social_categories"],
                p=PARAMS["mse_social_weights"],
            )

        records.append({
            "po_line_id": p_id,
            "procurement_channel": channel,
            "gem_order_id": gem_id,
            "mse_vendor_social_category": mse_soc,
        })

    df = pd.DataFrame(records)
    out_csv = LANDING_SAP / "EKKO_channel.csv"
    df.to_csv(out_csv, index=False)
    print(f"-> Wrote {len(df)} records to {out_csv}")
    return df


# ==============================================================================
# MAIN RUNNER
# ==============================================================================
def main():
    print(f"Starting gen_gap_sprint.py (SEED={SEED_BASE}+{RNG_OFFSET})...")
    df_env = generate_env_incidents()
    df_posh = generate_posh_cases()
    df_app = generate_apprentices()
    df_po = generate_po_channel()
    print("=== Gap sprint generation complete ===")
    print(f"env_incidents: {len(df_env)} rows")
    print(f"posh_cases:    {len(df_posh)} rows")
    print(f"apprentices:   {len(df_app)} rows (FY26={len(df_app[df_app['fiscal_year'] == 'FY26'])})")
    print(f"po_channel:    {len(df_po)} rows")


if __name__ == "__main__":
    main()
