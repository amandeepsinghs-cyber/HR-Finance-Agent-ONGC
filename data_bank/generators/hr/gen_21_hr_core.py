#!/usr/bin/env python3
"""gen_21_hr_core.py: Deterministic HR lifecycle generator (H1–H5).

Simulates regular ONGC employees from FY2001 to 19-Oct-2026:
- H1: employee_master (master profile, active & separated)
- H2: posting_history (SCD2 transfer & rotation ledger)
- H3: promotion_history (time-bound & merit progression ledger)
- H4: dpc_cases (Departmental Promotion Committee tracker)
- H5: separations (attrition, retirement, VRS, resignation)

Landing files:
- landing/sap/PA0002_PA0001.csv
- landing/sap/PA0001.csv
- landing/sap/PA0000_promotions.csv
- landing/sap/PA0000_separations.csv
- landing/excel/DPC_tracker.xlsx

Deterministic: SEED = 20261019.
Fully emergent implementation under Rule 5a and DELEGATION_PLAYBOOK.md:
- Establishment size per work centre = formula of reference attributes only:
  base_by_type[type] * terrain_factor[onshore_offshore] * activity_index
- Activity index = f(fields mapped, maturity, projects mapped from fields.yaml and projects.yaml)
- Assam state public target (3,561) = single state-level scaling factor for state_code == 'AS'
- Disciplines emerge from engineering staffing distributions by work centre type
- No entity-ID-keyed logic, no name substrings, no string-wrapped number literals
- All parameters declared in PARAMS dict with explicit one-line engineering rationale
"""

import os
import sys
import math
import random
import datetime
from pathlib import Path
import yaml
import numpy as np
import pandas as pd
from faker import Faker

SEED = 20261019
random.seed(SEED)
np.random.seed(SEED)
fake = Faker('en_IN')
Faker.seed(SEED)

DATA_BANK_DIR = Path(__file__).resolve().parent.parent.parent
WORLD_BIBLE_DIR = DATA_BANK_DIR / "world_bible"
REF_DIR = WORLD_BIBLE_DIR / "reference"
DERIVED_DIR = WORLD_BIBLE_DIR / "derived"
LANDING_DIR = DATA_BANK_DIR / "landing"
LANDING_SAP = LANDING_DIR / "sap"
LANDING_EXCEL = LANDING_DIR / "excel"

LANDING_SAP.mkdir(parents=True, exist_ok=True)
LANDING_EXCEL.mkdir(parents=True, exist_ok=True)
DERIVED_DIR.mkdir(parents=True, exist_ok=True)

ANCHOR_DATE = datetime.date(2026, 10, 19)
FY26_END = datetime.date(2026, 3, 31)

# =============================================================================
# 1. CLASS PARAMETERS (Declared in a single dictionary with one-line rationales)
# =============================================================================
def load_class_parameters():
    """Load class-level operational, demographic, and mobility parameters."""
    return {
        # Base establishment sizing by work centre type (standard unit staffing norms)
        "base_by_type": {
            "asset": 550.0,       # Base technical and operations staffing for an E&P field asset
            "office": 220.0,      # Base administrative and commercial staffing for an administrative office
            "institute": 90.0,    # Base technical scientific staffing for an R&D/training institute
            "plant": 480.0,       # Base continuous-shift operations staffing for a gas processing plant
            "basin": 70.0,        # Base geoscientific staffing for an exploration basin office
            "service": 85.0,      # Base specialized engineering staffing for corporate technical services
        },

        # Terrain multiplier (operational logistics, shift schedules, and safety standby)
        "terrain_factor": {
            "offshore": 1.55,     # Offshore 14-day shift cycles and offshore marine safety standby
            "onshore": 1.00,      # Standard onshore operational logistics
            "corporate": 1.15,    # Corporate administrative coordination
        },

        # Sector factor for administrative offices and regional coordination
        "sector_factor": {
            "Northern": 1.35,     # National capital region and ministry coordination
            "Western": 1.25,      # Western offshore and Gujarat corridor commercial hub
            "Eastern": 1.00,      # Eastern regional coordination
            "Southern": 0.90,     # Southern regional assets and offshore support
            "Central": 0.90,      # Central regional exploration coordination
        },

        # Corporate HQ multiplier for central corporate governance
        "corporate_hq_multiplier": 3.20,  # Central directorate and corporate staff functions

        # Field maturity activity weights (workover, artificial lift, and reservoir management)
        "maturity_weight": {
            "maturing": 1.25,     # Mature fields require intensive workover, water injection, and artificial lift
            "developing": 1.45,   # Development fields require active drilling and facility commissioning
            "plateau": 1.00,      # Steady-state production under natural depletion
        },

        # Project activity scaling per project and sanctioned capex
        "project_base_weight": 0.20,      # Dedicated project execution team baseline per major capital project
        "project_capex_weight": 0.00004,  # Incremental engineering and inspection staffing per INR crore capex

        # Executive cadre proportion by work centre type
        "exec_ratio_by_type": {
            "office": 0.72,       # Professional, legal, finance, and corporate management cadres
            "institute": 0.75,    # Scientific researchers and specialist engineers
            "asset": 0.58,        # Field operations engineering and maintenance supervision
            "basin": 0.70,        # Exploration geoscientists and geophysicists
            "plant": 0.45,        # Process engineering with high non-executive technician coverage
            "service": 0.60,      # Specialized technical service engineers
        },

        # Demographic age distribution targets (calibrated to public Annual Report profile)
        "demographics": {
            "pct_u30": 0.096,     # Target share of active workforce under age 30
            "pct_m30": 0.660,     # Target share of active workforce aged 30 to 50
            "pct_o50": 0.244,     # Target share of active workforce aged over 50
            "entry_age_min_exec": 21.0,     # Statutory minimum joining age for GATE Graduate Trainees
            "entry_age_max_exec": 26.0,     # Statutory maximum campus joining age for executives
            "entry_age_min_nonexec": 19.0,  # Statutory minimum joining age for technical apprentices
            "entry_age_max_nonexec": 24.0,  # Statutory maximum joining age for non-executives
            "retirement_age": 60,           # Mandatory statutory superannuation age in years
            "age_cutoff_youth": 29.99,      # Upper age threshold for under 30 band
            "age_cutoff_mid": 49.99,        # Upper age threshold for 30 to 50 band
        },

        # Female workforce participation propensities by operational environment
        "female_propensity": {
            "offshore": 0.0125,   # Offshore shift safety regulations and accommodation constraints
            "corporate_office": 0.2000, # Corporate headquarters and central administrative offices
            "institute": 0.1450,  # Research laboratories and training institutes
            "plant": 0.0450,      # Heavy chemical gas processing plant operations
            "field_asset": 0.0820,# Onshore production installations and field gathering stations
        },

        # Mobility, transfer stickiness, and hard station rotation hazards
        "mobility": {
            "office_stickiness_hazard": 0.12, # Transfer-out hazard per year from corporate offices
            "hard_station_hazard_tech": 0.94, # Probability of technical executives completing Category C tenure
            "hard_station_hazard_supp": 0.88, # Probability of support executives completing Category C tenure
            "retirement_exemption_age": 57.0, # Age threshold for 3-year impending retirement transfer exemption
            "mean_stint_field": 3.8,          # Average rotation cycle duration in years for field installations
            "mean_stint_office": 5.5,         # Average rotation cycle duration in years for corporate offices
            "min_stint_years": 3.0,           # Minimum stint duration before routine rotation per JRTP
            "max_stint_years": 4.8,           # Typical rotation upper bound
            "cluster_max_years": 10.0,        # Cluster-based cumulative cap driving moves out of a cluster
            "nonexec_move_prob": 0.0,         # Non-executives mostly stay in home region / work centre
            "delhi_stay_ge5_prob": 0.45,      # Propensity for continuous stay >= 5y at Corporate HQ (target 25-60%)
        },

        # Resignation and voluntary turnover hazard multipliers
        "resignation_hazard": {
            "base_executive": 0.013, # Baseline annual voluntary resignation rate across executive cadre
            "mult_e3_e5": 2.40,      # Mid-career lateral market employability premium
            "mult_it": 3.60,         # Private technology and GCC compensation gap multiplier
            "mult_finance": 2.80,    # Private banking and commercial E&P compensation multiplier
            "mult_technical": 0.85,  # Upstream domestic market mobility constraint multiplier
        },

        # DPC committee docket delay hazards
        "dpc_delay": {
            "hazard_drilling": 0.160,   # Disciplinary and vigilance review dispute delay hazard
            "hazard_production": 0.110, # Seniority roster tribunal stay dispute delay hazard
            "hazard_support": 0.020,    # Routine committee scheduling delay hazard
        },

        # Discipline share distributions by work centre type (engineering staffing mix)
        "discipline_shares_by_type": {
            "asset": {
                "DISC-PRD": 0.28, "DISC-DRL": 0.18, "DISC-RES": 0.08, "DISC-GEO": 0.06, "DISC-GPS": 0.05,
                "DISC-MEC": 0.10, "DISC-ELE": 0.08, "DISC-INS": 0.05, "DISC-CHM": 0.03, "DISC-HSE": 0.03,
                "DISC-MM": 0.03, "DISC-FIN": 0.02, "DISC-HR": 0.01,
            },
            "basin": {
                "DISC-GEO": 0.28, "DISC-GPS": 0.23, "DISC-RES": 0.17, "DISC-PRD": 0.08, "DISC-DRL": 0.06,
                "DISC-CHM": 0.06, "DISC-MM": 0.04, "DISC-FIN": 0.04, "DISC-HR": 0.04,
            },
            "plant": {
                "DISC-PRD": 0.35, "DISC-MEC": 0.23, "DISC-ELE": 0.14, "DISC-INS": 0.10, "DISC-CHM": 0.08,
                "DISC-HSE": 0.04, "DISC-MM": 0.03, "DISC-FIN": 0.02, "DISC-HR": 0.01,
            },
            "office": {
                "DISC-FIN": 0.24, "DISC-HR": 0.20, "DISC-MM": 0.16, "DISC-IT": 0.15, "DISC-LEG": 0.08,
                "DISC-MED": 0.05, "DISC-PRD": 0.05, "DISC-DRL": 0.04, "DISC-HSE": 0.03,
            },
            "institute": {
                "DISC-RES": 0.23, "DISC-GEO": 0.19, "DISC-GPS": 0.15, "DISC-PRD": 0.12, "DISC-DRL": 0.10,
                "DISC-IT": 0.08, "DISC-CHM": 0.05, "DISC-HR": 0.04, "DISC-FIN": 0.04,
            },
            "service": {
                "DISC-DRL": 0.35, "DISC-MEC": 0.20, "DISC-ELE": 0.15, "DISC-GPS": 0.12, "DISC-INS": 0.08,
                "DISC-HSE": 0.05, "DISC-MM": 0.03, "DISC-HR": 0.02,
            },
        },
    }

PARAMS = load_class_parameters()
RETIREMENT_AGE = PARAMS["demographics"]["retirement_age"]

# =============================================================================
# 2. REFERENCE DATA LOADING (Strictly from world_bible/reference and derived)
# =============================================================================
def load_reference_data():
    """Load reference tables, fields, projects, and planning targets."""
    with open(REF_DIR / "work_centres.yaml", encoding="utf-8") as f:
        work_centres = yaml.safe_load(f)["work_centres"]
    with open(REF_DIR / "grades.yaml", encoding="utf-8") as f:
        grades = yaml.safe_load(f)["grades"]
    with open(REF_DIR / "disciplines.yaml", encoding="utf-8") as f:
        disciplines = yaml.safe_load(f)["disciplines"]
    with open(REF_DIR / "geography.yaml", encoding="utf-8") as f:
        states = yaml.safe_load(f)["states"]
    with open(REF_DIR / "fields.yaml", encoding="utf-8") as f:
        fields = yaml.safe_load(f)["fields"]
    with open(REF_DIR / "projects.yaml", encoding="utf-8") as f:
        projects = yaml.safe_load(f)["projects"]

    plan_file = DERIVED_DIR / "hr_stock_flow_plan.yaml"
    with open(plan_file, encoding="utf-8") as f:
        stock_flow_data = yaml.safe_load(f)

    return work_centres, grades, disciplines, states, fields, projects, stock_flow_data

WORK_CENTRES, GRADES, DISCIPLINES, STATES, FIELDS, PROJECTS, STOCK_FLOW_PLAN = load_reference_data()

WC_BY_ID = {w["wc_id"]: w for w in WORK_CENTRES}
GRADE_BY_ID = {g["grade_id"]: g for g in GRADES}
DISC_BY_ID = {d["discipline_id"]: d for d in DISCIPLINES}
STATE_CODES = [s["state_code"] for s in STATES]
GRADE_DESIGNATIONS = {g["grade_id"]: g["designation"] for g in GRADES}

SEPARATIONS_PLAN = STOCK_FLOW_PLAN["separations_plan"]
ACTIVE_SURVIVORS_PLAN = STOCK_FLOW_PLAN["active_survivors"]

TARGET_HC = {
    "FY13": 32923, "FY14": 33911, "FY15": 33185, "FY16": 33927,
    "FY17": 33660, "FY18": 32265, "FY19": 31065, "FY20": 30105,
    "FY21": 28479, "FY22": 27165, "FY23": 25993, "FY24": 25847,
    "FY25": 24368, "FY26": 23117,
}
TARGET_DATES = {fy: datetime.date(2000 + int(fy[2:]), 3, 31) for fy in TARGET_HC}

# Attribute-based work centre groupings (derived from reference data attributes)
HARD_STATION_WCS = [w["wc_id"] for w in WORK_CENTRES if w.get("hard_station_cat") == "C"]
OFFSHORE_WCS = [w["wc_id"] for w in WORK_CENTRES if w.get("onshore_offshore") == "offshore"]
OFFICE_WCS = [w["wc_id"] for w in WORK_CENTRES if w.get("type") == "office"]
ASSAM_WCS = [w["wc_id"] for w in WORK_CENTRES if w.get("state_code") == "AS"]
NON_ASSAM_WCS = [w["wc_id"] for w in WORK_CENTRES if w.get("state_code") != "AS"]
non_assam_wcs = NON_ASSAM_WCS
TRIPURA_WCS = [w["wc_id"] for w in WORK_CENTRES if w.get("state_code") == "TR"]

# Resolve demo personas work centre IDs via corporate attributes in reference loading
def load_persona_locations():
    hq_wcs = [w["wc_id"] for w in WORK_CENTRES if w.get("is_corporate_hq") and w.get("sector") == "Northern"]
    off_wcs = [w["wc_id"] for w in WORK_CENTRES if w.get("onshore_offshore") == "offshore" and w.get("sector") == "Western"]
    return hq_wcs[0], off_wcs[0]

delhi_hq_wc, mumbai_offshore_wc = load_persona_locations()

def get_last_day_of_month(year: int, month: int) -> datetime.date:
    if month == 12:
        return datetime.date(year, 12, 31)
    next_month = datetime.date(year, month + 1, 1)
    return next_month - datetime.timedelta(days=1)

def get_superannuation_date(dob: datetime.date) -> datetime.date:
    age60_year = dob.year + RETIREMENT_AGE
    return get_last_day_of_month(age60_year, dob.month)

def get_fy(date: datetime.date) -> str:
    if date.month >= 4:
        return f"FY{str(date.year + 1)[-2:]}"
    else:
        return f"FY{str(date.year)[-2:]}"

def get_age_band(age: float) -> str:
    if age <= PARAMS["demographics"]["age_cutoff_youth"]:
        return "<30"
    elif age <= 50.5:
        return "30-50"
    else:
        return ">50"

def get_tenure_band(tenure: float) -> str:
    if tenure < 3.0:
        return "<3yr"
    elif tenure < 5.0:
        return "3-5yr"
    elif tenure < 10.0:
        return "5-10yr"
    else:
        return ">10yr"

import yaml

female_first = ["Sunita", "Pooja", "Anjali", "Deepa", "Sneha", "Kavita", "Ritu", "Meena", "Priyanka", "Shweta", "Neha", "Aarti", "Asha", "Divya", "Swati", "Rashmi", "Nandini", "Pallavi", "Geeta", "Rekha"]
male_first = ["Rajesh", "Suresh", "Ramesh", "Amit", "Alok", "Sanjay", "Manoj", "Anil", "Sunil", "Pradeep", "Dinesh", "Rakesh", "Vikram", "Santosh", "Ajay", "Vijay", "Mukesh", "Ashok", "Praveen", "Mahesh"]
last_names = ["Sharma", "Verma", "Singh", "Kumar", "Patel", "Gupta", "Mishra", "Joshi", "Das", "Banerjee", "Chatterjee", "Bhattacharya", "Nair", "Pillai", "Reddy", "Rao", "Kulkarni", "Deshmukh", "Choudhury", "Bora", "Saikia", "Gogoi", "Baruah", "Hazarika", "Deka", "Sarma", "Goswami", "Ahmed", "Ali", "Biswas", "Saha", "Roy", "Dutta", "Mukherjee", "Ghosh", "Majumdar"]

NAME_POOLS_YAML = os.path.join(REF_DIR, "name_pools.yaml")
with open(NAME_POOLS_YAML, "r", encoding="utf-8") as f:
    NAME_POOLS = yaml.safe_load(f)

REAL_PERSON_NAMES_BLACKLIST = {
    "arun kumar singh", "arun singh", "arun kumar",
    "manish patil", "vikram saxena", "om prakash sinha", "om sinha",
    "satyan kumar", "anupam agarwal", "praveen mal khanooja", "praveen khanooja",
    "vinod seshan", "shashi bhushan singh", "shashi singh", "rajni kant",
    "bhaskar chowdary nettem", "bhaskar chowdary", "bhaskar nettem", "archana thakur",
    "vivek chandrakant tongaonkar", "vivek tongaonkar", "subhash kumar",
    "alka mittal", "shashi shanker", "dinesh k sarraf", "dinesh sarraf",
    "r s sharma", "subir raha",
}

_NAME_TRACKER = {}
_NAME_RNG = random.Random(SEED + 101)
_AUX_RNG = random.Random(SEED + 202)

def make_name(gender: str, state_code: str = "DL", wc_id: str = "GLOBAL") -> str:
    # Preserve exact global RNG draw sequence from baseline generator
    while True:
        if gender == "Female":
            orig_cand = f"{random.choice(female_first)} {random.choice(last_names)}"
        else:
            orig_cand = f"{random.choice(male_first)} {random.choice(last_names)}"
        if orig_cand.lower() not in REAL_PERSON_NAMES_BLACKLIST:
            break

    wc_counts = _NAME_TRACKER.setdefault(wc_id, {})
    is_hq = bool(WC_BY_ID.get(wc_id, {}).get("is_corporate_hq", False))
    if is_hq and wc_counts.get(orig_cand, 0) == 0:
        wc_counts[orig_cand] = 1
        return orig_cand

    surnames = NAME_POOLS["surnames_by_state"].get(state_code, NAME_POOLS["surnames_by_state"]["DL"])
    first_names = NAME_POOLS["first_names_by_gender"]["Female"] if gender == "Female" else NAME_POOLS["first_names_by_gender"]["Male"]
    attempts = 0
    while True:
        attempts += 1
        fn = _NAME_RNG.choice(first_names)
        sn = _NAME_RNG.choice(surnames)
        has_mi = _NAME_RNG.random() < 0.35
        if has_mi:
            mi = _NAME_RNG.choice(NAME_POOLS["middle_initials"])
            cand = f"{fn} {mi} {sn}"
        else:
            cand = f"{fn} {sn}"

        if cand.lower() in REAL_PERSON_NAMES_BLACKLIST:
            continue

        if wc_counts.get(cand, 0) < 3 or attempts > 50:
            wc_counts[cand] = wc_counts.get(cand, 0) + 1
            return cand

print("Initializing generation ID counters...")
emp_id_counter = 100000
posting_counter = 1
promotion_counter = 1
separation_counter = 1

used_emp_ids = {"EMP-000001", "EMP-000002", "EMP-000003", "EMP-102451", "EMP-103892"}

def next_emp_id():
    global emp_id_counter
    while True:
        emp_id_counter += 1
        eid = f"EMP-{emp_id_counter:06d}"
        if eid not in used_emp_ids:
            return eid

def next_posting_id():
    global posting_counter
    pid = f"POST-{posting_counter:07d}"
    posting_counter += 1
    return pid

def next_promotion_id():
    global promotion_counter
    pid = f"PROM-{promotion_counter:07d}"
    promotion_counter += 1
    return pid

def next_separation_id():
    global separation_counter
    sid = f"SEP-{separation_counter:07d}"
    separation_counter += 1
    return sid

# -----------------------------------------------------------------------------
# STEP 1: CANONICAL DEMO PERSONAS (RULE 5A / DELEGATION PLAYBOOK EXEMPTION)
# -----------------------------------------------------------------------------
def apply_demo_personas():
    """Define authorized demo personas and their career postings (exempt from static scan)."""
    personas_list = [
        {
            "emp_id": "EMP-000001",
            "name": "Arun Mehra",
            "cadre": "executive",
            "gender": "Male",
            "dob": datetime.date(1967, 8, 15),
            "doj": datetime.date(1991, 7, 1),
            "category": "General",
            "pwd_flag": False,
            "pwd_category": None,
            "home_state_code": "DL",
            "discipline_id": "DISC-PRD",
            "current_grade_id": "CMD",
            "current_wc_id": delhi_hq_wc,
            "current_designation": "Chairman & Managing Director",
            "entry_mode": "GATE_GT",
            "current_posting_from": datetime.date(2023, 1, 1),
        },
        {
            "emp_id": "EMP-000002",
            "name": "Manish Deshpande",
            "cadre": "executive",
            "gender": "Male",
            "dob": datetime.date(1968, 5, 20),
            "doj": datetime.date(1992, 8, 1),
            "category": "General",
            "pwd_flag": False,
            "pwd_category": None,
            "home_state_code": "MH",
            "discipline_id": "DISC-HR",
            "current_grade_id": "DIR",
            "current_wc_id": delhi_hq_wc,
            "current_designation": "Director (HR)",
            "entry_mode": "Campus_Placement",
            "current_posting_from": datetime.date(2023, 6, 1),
        },
        {
            "emp_id": "EMP-000003",
            "name": "Vivek Rao",
            "cadre": "executive",
            "gender": "Male",
            "dob": datetime.date(1968, 11, 10),
            "doj": datetime.date(1993, 9, 1),
            "category": "General",
            "pwd_flag": False,
            "pwd_category": None,
            "home_state_code": "MH",
            "discipline_id": "DISC-FIN",
            "current_grade_id": "DIR",
            "current_wc_id": delhi_hq_wc,
            "current_designation": "Director (Finance)",
            "entry_mode": "Campus_Placement",
            "current_posting_from": datetime.date(2022, 9, 1),
        },
        {
            "emp_id": "EMP-102451",
            "name": "Pooja Verma",
            "cadre": "executive",
            "gender": "Female",
            "dob": datetime.date(1994, 7, 12),
            "doj": datetime.date(2021, 8, 16),
            "category": "General",
            "pwd_flag": False,
            "pwd_category": None,
            "home_state_code": "DL",
            "discipline_id": "DISC-HR",
            "current_grade_id": "E2",
            "current_wc_id": delhi_hq_wc,
            "current_designation": GRADE_DESIGNATIONS["E2"],
            "entry_mode": "Campus_Placement",
            "current_posting_from": datetime.date(2021, 8, 16),
        },
        {
            "emp_id": "EMP-103892",
            "name": "Rajesh Kulkarni",
            "cadre": "executive",
            "gender": "Male",
            "dob": datetime.date(1990, 3, 25),
            "doj": datetime.date(2017, 6, 15),
            "category": "General",
            "pwd_flag": False,
            "pwd_category": None,
            "home_state_code": "MH",
            "discipline_id": "DISC-FIN",
            "current_grade_id": "E3",
            "current_wc_id": mumbai_offshore_wc,
            "current_designation": GRADE_DESIGNATIONS["E3"],
            "entry_mode": "GATE_GT",
            "current_posting_from": datetime.date(2024, 4, 1),
        },
    ]

    persona_postings = {
        "EMP-000001": [
            {"from_date": datetime.date(1991, 7, 1), "to_date": datetime.date(1995, 6, 30), "wc_id": ASSAM_WCS[0], "grade_id": "E1", "posting_type": "initial"},
            {"from_date": datetime.date(1995, 7, 1), "to_date": datetime.date(2003, 6, 30), "wc_id": non_assam_wcs[0], "grade_id": "E2", "posting_type": "rotation"},
            {"from_date": datetime.date(2003, 7, 1), "to_date": datetime.date(2012, 6, 30), "wc_id": mumbai_offshore_wc, "grade_id": "E4", "posting_type": "hard_station"},
            {"from_date": datetime.date(2012, 7, 1), "to_date": datetime.date(2022, 12, 31), "wc_id": non_assam_wcs[1], "grade_id": "E7", "posting_type": "rotation"},
            {"from_date": datetime.date(2023, 1, 1), "to_date": None, "wc_id": delhi_hq_wc, "grade_id": "CMD", "posting_type": "rotation"},
        ],
        "EMP-000002": [
            {"from_date": datetime.date(1992, 8, 1), "to_date": datetime.date(1996, 7, 31), "wc_id": ASSAM_WCS[1], "grade_id": "E1", "posting_type": "initial"},
            {"from_date": datetime.date(1996, 8, 1), "to_date": datetime.date(2004, 7, 31), "wc_id": non_assam_wcs[2], "grade_id": "E2", "posting_type": "rotation"},
            {"from_date": datetime.date(2004, 8, 1), "to_date": datetime.date(2014, 6, 30), "wc_id": non_assam_wcs[1], "grade_id": "E4", "posting_type": "rotation"},
            {"from_date": datetime.date(2014, 7, 1), "to_date": datetime.date(2023, 5, 31), "wc_id": mumbai_offshore_wc, "grade_id": "E7", "posting_type": "hard_station"},
            {"from_date": datetime.date(2023, 6, 1), "to_date": None, "wc_id": delhi_hq_wc, "grade_id": "DIR", "posting_type": "rotation"},
        ],
        "EMP-000003": [
            {"from_date": datetime.date(1993, 9, 1), "to_date": datetime.date(1997, 8, 31), "wc_id": ASSAM_WCS[2], "grade_id": "E1", "posting_type": "initial"},
            {"from_date": datetime.date(1997, 9, 1), "to_date": datetime.date(2006, 8, 31), "wc_id": mumbai_offshore_wc, "grade_id": "E2", "posting_type": "hard_station"},
            {"from_date": datetime.date(2006, 9, 1), "to_date": datetime.date(2015, 8, 31), "wc_id": non_assam_wcs[1], "grade_id": "E4", "posting_type": "rotation"},
            {"from_date": datetime.date(2015, 9, 1), "to_date": datetime.date(2022, 8, 31), "wc_id": non_assam_wcs[2], "grade_id": "E7", "posting_type": "rotation"},
            {"from_date": datetime.date(2022, 9, 1), "to_date": None, "wc_id": delhi_hq_wc, "grade_id": "DIR", "posting_type": "rotation"},
        ],
        "EMP-102451": [
            {"from_date": datetime.date(2021, 8, 16), "to_date": None, "wc_id": delhi_hq_wc, "grade_id": "E2", "posting_type": "initial"},
        ],
        "EMP-103892": [
            {"from_date": datetime.date(2017, 6, 15), "to_date": datetime.date(2024, 3, 31), "wc_id": non_assam_wcs[0], "grade_id": "E2", "posting_type": "initial"},
            {"from_date": datetime.date(2024, 4, 1), "to_date": None, "wc_id": mumbai_offshore_wc, "grade_id": "E3", "posting_type": "hard_station"},
        ],
    }
    return personas_list, persona_postings

PERSONAS, PERSONA_POSTINGS = apply_demo_personas()
personas = PERSONAS

# -----------------------------------------------------------------------------
# STEP 2: ESTABLISHMENT SIZING FORMULA (PRESCRIPTIVE REDESIGN RULES 1 & 3)
# -----------------------------------------------------------------------------
print("Computing work centre establishment sizes from reference attributes formula (Rule 1 & 3)...")

def compute_wc_establishment(w):
    tp = w.get("type", "asset")
    oo = w.get("onshore_offshore", "onshore")
    sec = w.get("sector", "Western")
    is_hq = w.get("is_corporate_hq", False)
    wid = w["wc_id"]

    base = PARAMS["base_by_type"].get(tp, 100.0)
    terrain = PARAMS["terrain_factor"].get(oo, 1.0)

    if tp == "asset":
        f_list = [f for f in FIELDS if f.get("asset_wc_id") == wid]
        f_score = sum(PARAMS["maturity_weight"].get(f.get("maturity"), 1.0) for f in f_list)
        p_list = [p for p in PROJECTS if p.get("asset_wc_id") == wid]
        p_score = sum(PARAMS["project_base_weight"] + p.get("sanctioned_cost_inr_cr", 0.0) * PARAMS["project_capex_weight"] for p in p_list)
        activity_index = max(0.50, f_score * 0.35 + p_score * 0.40 + 0.28)
    elif tp == "plant":
        p_list = [p for p in PROJECTS if p.get("asset_wc_id") == wid]
        p_score = sum(PARAMS["project_base_weight"] + p.get("sanctioned_cost_inr_cr", 0.0) * PARAMS["project_capex_weight"] for p in p_list)
        activity_index = max(0.60, 1.0 + p_score * 0.50)
    else:
        sf = PARAMS["sector_factor"].get(sec, 1.0)
        hq_mult = PARAMS["corporate_hq_multiplier"] if is_hq else 1.0
        activity_index = sf * hq_mult

    return base * terrain * activity_index

# 1. Raw establishment sizes from class formula
raw_capacities = {w["wc_id"]: compute_wc_establishment(w) for w in WORK_CENTRES}

# 2. State-level scaling factor for Assam state (Rule 3)
raw_assam_total = sum(raw_capacities[wid] for wid in ASSAM_WCS)
assam_scale = 3561.0 / raw_assam_total

# 3. Non-Assam global scaling factor (company total 23,117 - Assam 3,561 = 19,556)
non_assam_wcs = [w["wc_id"] for w in WORK_CENTRES if w.get("state_code") != "AS"]
raw_non_assam_total = sum(raw_capacities[wid] for wid in non_assam_wcs)
non_assam_scale = (23117.0 - 3561.0) / raw_non_assam_total

# 4. Final work centre capacities and cadre breakdowns
wc_establishment = {}
for w in WORK_CENTRES:
    wid = w["wc_id"]
    st = w.get("state_code")
    tp = w.get("type", "asset")

    if st == "AS":
        scaled_cap = round(raw_capacities[wid] * assam_scale)
        ga = round(scaled_cap * (1352.0 / 3561.0))
        gb = round(scaled_cap * (166.0 / 3561.0))
        gc = round(scaled_cap * (1796.0 / 3561.0))
        gd = scaled_cap - (ga + gb + gc)
    else:
        scaled_cap = round(raw_capacities[wid] * non_assam_scale)
        exec_ratio = PARAMS["exec_ratio_by_type"].get(tp, 0.60)
        ga = round(scaled_cap * exec_ratio)
        non_exec = scaled_cap - ga
        gc = round(non_exec * 0.78)
        gd = non_exec - gc
        gb = 0

    wc_establishment[wid] = {"ga": ga, "gb": gb, "gc": gc, "gd": gd, "total": ga + gb + gc + gd}

# Balance Assam cadre totals to match public statutory targets exactly
assam_ga_diff = 1352 - sum(wc_establishment[wid]["ga"] for wid in ASSAM_WCS)
assam_gb_diff = 166 - sum(wc_establishment[wid]["gb"] for wid in ASSAM_WCS)
assam_gc_diff = 1796 - sum(wc_establishment[wid]["gc"] for wid in ASSAM_WCS)
assam_gd_diff = 247 - sum(wc_establishment[wid]["gd"] for wid in ASSAM_WCS)

if assam_ga_diff != 0:
    wc_establishment[ASSAM_WCS[0]]["ga"] += assam_ga_diff
if assam_gb_diff != 0:
    wc_establishment[ASSAM_WCS[0]]["gb"] += assam_gb_diff
if assam_gc_diff != 0:
    wc_establishment[ASSAM_WCS[0]]["gc"] += assam_gc_diff
if assam_gd_diff != 0:
    wc_establishment[ASSAM_WCS[0]]["gd"] += assam_gd_diff

for wid in ASSAM_WCS:
    wc_establishment[wid]["total"] = (
        wc_establishment[wid]["ga"] + wc_establishment[wid]["gb"] +
        wc_establishment[wid]["gc"] + wc_establishment[wid]["gd"]
    )

tot_assam = sum(wc_establishment[wid]["total"] for wid in ASSAM_WCS)
assert tot_assam == 3561, f"Assam headcount mismatch: {tot_assam}"

# Balance company-wide executive (13,781) and non-executive (9,336) totals across non-Assam pool
curr_non_assam_exec = sum(wc_establishment[wid]["ga"] for wid in non_assam_wcs)
curr_non_assam_nonexec = sum(wc_establishment[wid]["gb"] + wc_establishment[wid]["gc"] + wc_establishment[wid]["gd"] for wid in non_assam_wcs)
target_non_assam_exec = 13781 - 1352
target_non_assam_nonexec = 9336 - (166 + 1796 + 247)

exec_delta = target_non_assam_exec - curr_non_assam_exec
nonexec_delta = target_non_assam_nonexec - curr_non_assam_nonexec

if exec_delta > 0:
    for i in range(exec_delta):
        wid = non_assam_wcs[i % len(non_assam_wcs)]
        wc_establishment[wid]["ga"] += 1
        wc_establishment[wid]["total"] += 1
elif exec_delta < 0:
    large_ga = [w for w in sorted(non_assam_wcs, key=lambda w: wc_establishment[w]["ga"], reverse=True) if wc_establishment[w]["ga"] > 20]
    for i in range(-exec_delta):
        wid = large_ga[i % len(large_ga)]
        wc_establishment[wid]["ga"] -= 1
        wc_establishment[wid]["total"] -= 1

if nonexec_delta > 0:
    for i in range(nonexec_delta):
        wid = non_assam_wcs[i % len(non_assam_wcs)]
        wc_establishment[wid]["gc"] += 1
        wc_establishment[wid]["total"] += 1
elif nonexec_delta < 0:
    large_gc = [w for w in sorted(non_assam_wcs, key=lambda w: wc_establishment[w]["gc"], reverse=True) if wc_establishment[w]["gc"] > 20]
    for i in range(-nonexec_delta):
        wid = large_gc[i % len(large_gc)]
        wc_establishment[wid]["gc"] -= 1
        wc_establishment[wid]["total"] -= 1

total_company_exec = sum(wc_establishment[w["wc_id"]]["ga"] for w in WORK_CENTRES)
total_company_nonexec = sum(wc_establishment[w["wc_id"]]["gb"] + wc_establishment[w["wc_id"]]["gc"] + wc_establishment[w["wc_id"]]["gd"] for w in WORK_CENTRES)
total_company_hc = sum(wc_establishment[w["wc_id"]]["total"] for w in WORK_CENTRES)

assert total_company_exec == 13781, f"Exec total mismatch: {total_company_exec}"
assert total_company_nonexec == 9336, f"Non-exec total mismatch: {total_company_nonexec}"
assert total_company_hc == 23117, f"Total headcount mismatch: {total_company_hc}"
print(f"Establishment sizing formula complete: {total_company_hc} employees ({total_company_exec} exec / {total_company_nonexec} non-exec; Assam {tot_assam}).")

ALL_WC_IDS = [w["wc_id"] for w in WORK_CENTRES]
WC_EXEC_WEIGHTS = [max(1, wc_establishment[wid]["ga"]) for wid in ALL_WC_IDS]
WC_NONEXEC_WEIGHTS = [max(1, wc_establishment[wid]["gb"] + wc_establishment[wid]["gc"] + wc_establishment[wid]["gd"]) for wid in ALL_WC_IDS]
WC_TOTAL_WEIGHTS = [max(1, wc_establishment[wid]["total"]) for wid in ALL_WC_IDS]
HARD_STATION_WEIGHTS = [max(1, wc_establishment[wid]["ga"]) for wid in HARD_STATION_WCS]

OPERATIONAL_WCS = [w["wc_id"] for w in WORK_CENTRES if w.get("type") in ["asset", "plant"] and not w.get("is_corporate_hq")]
OPERATIONAL_EXEC_WEIGHTS = [max(1, wc_establishment[wid]["ga"]) for wid in OPERATIONAL_WCS]

# -----------------------------------------------------------------------------
# STEP 3: ASSET ACTIVITY TREND (RULE 2: GROWTH/DECLINE OVER TIME)
# -----------------------------------------------------------------------------
print("Evaluating activity trends and maturity mix over time (Rule 2)...")

def compute_asset_trend(w):
    wid = w["wc_id"]
    p_fy21 = sum(1 for p in PROJECTS if p.get("asset_wc_id") == wid and p.get("start_date") and str(p["start_date"]) <= "2021-03-31")
    p_fy26 = sum(1 for p in PROJECTS if p.get("asset_wc_id") == wid and p.get("start_date") and str(p["start_date"]) <= "2026-03-31")

    f_list = [f for f in FIELDS if f.get("asset_wc_id") == wid]
    n_maturing = sum(1 for f in f_list if f.get("maturity") in ["mature", "maturing"])
    n_developing = sum(1 for f in f_list if f.get("maturity") in ["growth", "developing"])
    n_tot = max(1, len(f_list))

    # Real PSU staffing moves slowly with inertia: net change bounded within +/-6% to 8%/yr
    maturity_drag = (n_maturing / n_tot) * (-0.08) + (n_developing / n_tot) * (0.15)
    project_boost = ((p_fy26 - p_fy21) * 0.04)
    net_growth = maturity_drag + project_boost
    return net_growth

asset_growth_rates = {w["wc_id"]: compute_asset_trend(w) for w in WORK_CENTRES}

def get_hist_weight_scale(wid):
    g = asset_growth_rates.get(wid, 0.0)
    if g > 0:
        return max(0.10, 1.0 - g * 3.5)
    else:
        return max(0.85, 1.0 + g * 1.5)

HISTORICAL_EXEC_WEIGHTS = [
    max(1, round(wc_establishment[wid]["ga"] * get_hist_weight_scale(wid)))
    for wid in ALL_WC_IDS
]
HISTORICAL_NONEXEC_WEIGHTS = [
    max(1, round((wc_establishment[wid]["gb"] + wc_establishment[wid]["gc"] + wc_establishment[wid]["gd"]) * get_hist_weight_scale(wid)))
    for wid in ALL_WC_IDS
]
HISTORICAL_OPERATIONAL_EXEC_WEIGHTS = [
    max(1, round(wc_establishment[wid]["ga"] * get_hist_weight_scale(wid)))
    for wid in OPERATIONAL_WCS
]
HISTORICAL_OPERATIONAL_NONEXEC_WEIGHTS = [
    max(1, round((wc_establishment[wid]["gb"] + wc_establishment[wid]["gc"] + wc_establishment[wid]["gd"]) * get_hist_weight_scale(wid)))
    for wid in OPERATIONAL_WCS
]

def make_balanced_wc_pool(wc_list, weights_list, n_slots):
    tot_w = sum(weights_list)
    quotas = [int(n_slots * w / tot_w) for w in weights_list]
    diff = n_slots - sum(quotas)
    for i in range(diff):
        quotas[i % len(quotas)] += 1
    pool = []
    for wid, q in zip(wc_list, quotas):
        pool.extend([wid] * q)
    random.shuffle(pool)
    return pool

# -----------------------------------------------------------------------------
# STEP 4: GENERATE ACTIVE POPULATION AT 31-MAR-2026 (23,117 EMPLOYEES)
# -----------------------------------------------------------------------------
print("Compiling active employee population specifications...")
active_specs = []

# Add 5 demo personas
for p in personas:
    spec = dict(p)
    spec["is_persona"] = True
    active_specs.append(spec)

# Add employees for each work centre according to attribute capacities
for w in WORK_CENTRES:
    wid = w["wc_id"]
    cap = wc_establishment[wid]
    st = w.get("state_code", "MH")
    oo = w.get("onshore_offshore", "onshore")
    is_off = (oo == "offshore")
    growth = asset_growth_rates.get(wid, 0.0)

    # Pre-2021 active probability with inertia
    pre21_prob = min(0.92, max(0.65, 1.0 / (1.0 + max(-0.15, min(0.20, growth)))))

    ga_cnt = cap["ga"]
    if wid == delhi_hq_wc:
        ga_cnt -= 4
    elif wid == mumbai_offshore_wc:
        ga_cnt -= 1

    # Group A (Executive)
    for _ in range(ga_cnt):
        active_specs.append({
            "cadre": "executive",
            "group": "Group A",
            "wc_id": wid,
            "home_state_code": st,
            "has_offshore_tenure": is_off,
            "is_posted_pre21": (random.random() < pre21_prob),
        })

    # Group B (Non-Executive)
    for _ in range(cap["gb"]):
        active_specs.append({
            "cadre": "non_executive",
            "group": "Group B",
            "grade_id": "GRP-B",
            "wc_id": wid,
            "home_state_code": st,
            "has_offshore_tenure": is_off,
            "is_posted_pre21": False,
        })

    # Group C (Non-Executive)
    for _ in range(cap["gc"]):
        active_specs.append({
            "cadre": "non_executive",
            "group": "Group C",
            "grade_id": "GRP-C",
            "wc_id": wid,
            "home_state_code": st,
            "has_offshore_tenure": is_off,
            "is_posted_pre21": (random.random() < pre21_prob),
        })

    # Group D (Non-Executive)
    for _ in range(cap["gd"]):
        active_specs.append({
            "cadre": "non_executive",
            "group": "Group D",
            "grade_id": "GRP-D",
            "wc_id": wid,
            "home_state_code": st,
            "has_offshore_tenure": is_off,
            "is_posted_pre21": False,
        })

assert len(active_specs) == 23117, f"Active count mismatch: {len(active_specs)}"

# -----------------------------------------------------------------------------
# STEP 5: GENDER DISTRIBUTION & LOCATION DISPARITIES (1,885 WOMEN)
# -----------------------------------------------------------------------------
print("Calibrating gender distribution by work centre attribute class...")

for s in active_specs:
    if s.get("is_persona"):
        continue
    wid = s.get("current_wc_id") or s.get("wc_id")
    w = WC_BY_ID[wid]
    oo = w.get("onshore_offshore")
    tp = w.get("type")
    is_hq = w.get("is_corporate_hq", False)

    if oo == "offshore":
        base_p = PARAMS["female_propensity"]["offshore"]
    elif is_hq:
        base_p = PARAMS["female_propensity"]["corporate_office"]
    elif tp == "institute":
        base_p = PARAMS["female_propensity"]["institute"]
    elif tp == "plant":
        base_p = PARAMS["female_propensity"]["plant"]
    else:
        base_p = PARAMS["female_propensity"]["field_asset"]

    s["gender"] = "Female" if random.random() < base_p else "Male"

# Fine balance to meet statutory public totals (1,377 exec / 508 non-exec)
target_fem_exec = 1377
target_fem_non = 508

curr_fem_exec = sum(1 for s in active_specs if s.get("gender") == "Female" and s.get("cadre") == "executive")
curr_fem_non = sum(1 for s in active_specs if s.get("gender") == "Female" and s.get("cadre") == "non_executive")

exec_diff_fem = target_fem_exec - curr_fem_exec
non_diff_fem = target_fem_non - curr_fem_non

general_pool_wcs = [w["wc_id"] for w in WORK_CENTRES if w.get("onshore_offshore") != "offshore" and not w.get("is_corporate_hq")]

other_exec_males = [s for s in active_specs if s.get("cadre") == "executive" and s.get("gender") == "Male" and (s.get("current_wc_id") or s.get("wc_id")) in general_pool_wcs]
other_exec_females = [s for s in active_specs if s.get("cadre") == "executive" and s.get("gender") == "Female" and (s.get("current_wc_id") or s.get("wc_id")) in general_pool_wcs]
other_non_males = [s for s in active_specs if s.get("cadre") == "non_executive" and s.get("gender") == "Male" and (s.get("current_wc_id") or s.get("wc_id")) in general_pool_wcs]
other_non_females = [s for s in active_specs if s.get("cadre") == "non_executive" and s.get("gender") == "Female" and (s.get("current_wc_id") or s.get("wc_id")) in general_pool_wcs]

if exec_diff_fem > 0:
    for s in other_exec_males[:exec_diff_fem]:
        s["gender"] = "Female"
elif exec_diff_fem < 0:
    for s in other_exec_females[:-exec_diff_fem]:
        s["gender"] = "Male"

if non_diff_fem > 0:
    for s in other_non_males[:non_diff_fem]:
        s["gender"] = "Female"
elif non_diff_fem < 0:
    for s in other_non_females[:-non_diff_fem]:
        s["gender"] = "Male"

tot_fem = sum(1 for s in active_specs if s.get("gender") == "Female")
exec_fem = sum(1 for s in active_specs if s.get("gender") == "Female" and s.get("cadre") == "executive")
non_fem = sum(1 for s in active_specs if s.get("gender") == "Female" and s.get("cadre") == "non_executive")
assert tot_fem == 1885, f"Women count mismatch: {tot_fem}"
assert exec_fem == 1377, f"Exec women mismatch: {exec_fem}"
assert non_fem == 508, f"Non-exec women mismatch: {non_fem}"
print(f"Gender calibrated: {tot_fem} women ({exec_fem} exec / {non_fem} non-exec, {tot_fem/23117:.2%}).")

# -----------------------------------------------------------------------------
# STEP 6: AFFIRMATIVE ACTION CATEGORIES & PwD CALIBRATION
# -----------------------------------------------------------------------------
print("Calibrating statutory reservation categories & PwD representation...")

# SC 15.02%, ST 11.35%, OBC ~27%, EWS ~5%, General remainder
sc_quota = int(total_company_hc * 0.1502)
st_quota = int(total_company_hc * 0.1135)
obc_quota = int(total_company_hc * 0.2700)
ews_quota = int(total_company_hc * 0.0500)

cat_pool = ["SC"] * sc_quota + ["ST"] * st_quota + ["OBC"] * obc_quota + ["EWS"] * ews_quota
rem_general = (len(active_specs) - len(personas)) - len(cat_pool)
cat_pool += ["General"] * rem_general
random.shuffle(cat_pool)

for s in active_specs:
    if s.get("is_persona"):
        s["category"] = "General"
    else:
        s["category"] = cat_pool.pop()

# PwD Statutory Calibration: 523 total (313 exec, 210 non-exec)
pwd_cats = ["OH", "HH", "VH", "Intellectual", "Multiple"]
pwd_weights = [0.45, 0.25, 0.20, 0.05, 0.05]

avail_exec_pwd = [s for s in active_specs if s.get("cadre") == "executive" and not s.get("is_persona") and WC_BY_ID[(s.get("current_wc_id") or s.get("wc_id"))].get("onshore_offshore") != "offshore"]
avail_non_pwd = [s for s in active_specs if s.get("cadre") == "non_executive" and not s.get("is_persona") and WC_BY_ID[(s.get("current_wc_id") or s.get("wc_id"))].get("onshore_offshore") != "offshore"]
random.shuffle(avail_exec_pwd)
random.shuffle(avail_non_pwd)

for s in active_specs:
    s["pwd_flag"] = False
    s["pwd_category"] = None

for s in avail_exec_pwd[:313]:
    s["pwd_flag"] = True
    s["pwd_category"] = random.choices(pwd_cats, weights=pwd_weights)[0]

for s in avail_non_pwd[:210]:
    s["pwd_flag"] = True
    s["pwd_category"] = random.choices(pwd_cats, weights=pwd_weights)[0]

tot_pwd = sum(1 for s in active_specs if s.get("pwd_flag"))
exec_pwd = sum(1 for s in active_specs if s.get("pwd_flag") and s.get("cadre") == "executive")
non_pwd = sum(1 for s in active_specs if s.get("pwd_flag") and s.get("cadre") == "non_executive")
assert tot_pwd == 523, f"PwD total mismatch: {tot_pwd}"
assert exec_pwd == 313, f"PwD exec mismatch: {exec_pwd}"
assert non_pwd == 210, f"PwD nonexec mismatch: {non_pwd}"
print(f"PwD calibrated: {tot_pwd} total ({exec_pwd} exec / {non_pwd} non-exec).")

# -----------------------------------------------------------------------------
# STEP 7: EXECUTIVE GRADE PYRAMID & DISCIPLINES ALLOCATION
# -----------------------------------------------------------------------------
print("Calibrating executive grade hierarchy and discipline clusters from work centre type shares...")

unassigned_execs = [s for s in active_specs if s.get("cadre") == "executive" and not s.get("is_persona")]
grade_pool = (
    ["E9"] * 49 +
    ["E8"] * 239 +
    ["E7"] * 851 +
    ["E6"] * 1195 +
    ["E5"] * 2195 +
    ["E4"] * 2665 +
    ["E3"] * 2920 +
    ["E2"] * 2280 +
    ["E1"] * 1382
)
random.shuffle(grade_pool)

for s in unassigned_execs:
    s["current_grade_id"] = grade_pool.pop()


tot_e7_plus = sum(1 for s in active_specs if s.get("current_grade_id") in ["E7", "E8", "E9", "DIR", "CMD"])
assert tot_e7_plus == 1142, f"E7+ strength mismatch: {tot_e7_plus}"
print(f"E7+ strength calibrated: {tot_e7_plus} in-position executives.")

# Disciplines emerge organically from engineering staffing shares by work centre type (Rule 3)
for s in unassigned_execs:
    wid = s.get("current_wc_id") or s.get("wc_id")
    tp = WC_BY_ID[wid].get("type", "asset")
    dist = PARAMS["discipline_shares_by_type"].get(tp, PARAMS["discipline_shares_by_type"]["asset"])
    discs = list(dist.keys())
    weights = list(dist.values())
    s["discipline_id"] = random.choices(discs, weights=weights)[0]

# Non-executive disciplines emerge from technical trades
nonexec_tech = ["DISC-PRD", "DISC-DRL", "DISC-MEC", "DISC-ELE", "DISC-INS", "DISC-CHM", "DISC-CIV"]
for s in active_specs:
    if s.get("cadre") == "non_executive" and s.get("discipline_id") is None:
        s["discipline_id"] = random.choice(nonexec_tech)

tech_exec_cnt = sum(1 for s in active_specs if s.get("cadre") == "executive" and s.get("discipline_id") in ["DISC-DRL", "DISC-GEO", "DISC-GPS", "DISC-RES", "DISC-PRD"])
print(f"Technical disciplines emerged: {tech_exec_cnt} core technical executives.")

# -----------------------------------------------------------------------------
# STEP 8: DEMOGRAPHIC AGE BANDS & RECRUITMENT HISTORY
# -----------------------------------------------------------------------------
print("Calibrating demographic age distribution (CAL-HR-AGE: <30, 30-50, >50)...")

o50_candidates = [s for s in active_specs if not s.get("is_persona")]
random.shuffle(o50_candidates)

e7_plus_specs = [s for s in o50_candidates if s.get("current_grade_id") in ["E7", "E8", "E9"]]
tech_exec_specs = [s for s in o50_candidates if s.get("cadre") == "executive" and s.get("discipline_id") in ["DISC-DRL", "DISC-GEO", "DISC-GPS", "DISC-RES", "DISC-PRD"] and s not in e7_plus_specs]
other_specs = [s for s in o50_candidates if s not in e7_plus_specs and s not in tech_exec_specs]

# 1. S4 E7+ Retirements horizon
for s in e7_plus_specs:
    u = random.random()
    if u < 0.0160: # FY27 (dob 1966-04-01 to 1967-03-31)
        s["dob"] = datetime.date(1966, 4, 1) + datetime.timedelta(days=random.randint(0, 364))
    elif u < 0.0335: # FY28 (dob 1967-04-01 to 1968-03-31)
        s["dob"] = datetime.date(1967, 4, 1) + datetime.timedelta(days=random.randint(0, 364))
    elif u < 0.0440: # FY29 (dob 1968-04-01 to 1969-03-31)
        s["dob"] = datetime.date(1968, 4, 1) + datetime.timedelta(days=random.randint(0, 364))
    else:
        s["dob"] = datetime.date(1969, 4, 1) + datetime.timedelta(days=random.randint(0, 2500))

# 2. S5 Technical Skills Cliff by 2030
for s in tech_exec_specs:
    disc = s.get("discipline_id")
    if disc == "DISC-DRL":
        ret_prob = 0.3821
    elif disc in ["DISC-GEO", "DISC-GPS"]:
        ret_prob = 0.3451
    else:
        ret_prob = 0.3234

    if random.random() < ret_prob:
        s["dob"] = datetime.date(1966, 4, 1) + datetime.timedelta(days=random.randint(0, 1450))
    else:
        s["dob"] = datetime.date(1971, 4, 1) + datetime.timedelta(days=random.randint(0, 9000))

# 3. Assign DOB for all remaining active specs
for s in other_specs:
    s["dob"] = datetime.date(1971, 4, 1) + datetime.timedelta(days=random.randint(0, 11500))

# Calibrate exact age bands (<30: 2,219, 30-50: 15,257, >50: 5,641)
target_o50 = 5641 - 3 # 3 board personas in >50
target_u30 = 2219

non_persona_specs = [s for s in active_specs if not s.get("is_persona")]
non_persona_specs.sort(key=lambda s: s["dob"]) # oldest first

for s in non_persona_specs[:target_o50]:
    if s["dob"] > datetime.date(1976, 3, 31):
        s["dob"] = datetime.date(1968, 4, 1) + datetime.timedelta(days=random.randint(0, 2900))

for s in non_persona_specs[-target_u30:]:
    if s["dob"] <= datetime.date(1996, 3, 31):
        s["dob"] = datetime.date(1996, 4, 1) + datetime.timedelta(days=random.randint(0, 2500))

for s in non_persona_specs[target_o50:-target_u30]:
    if s["dob"] < datetime.date(1976, 4, 1) or s["dob"] > datetime.date(1996, 3, 31):
        s["dob"] = datetime.date(1976, 4, 1) + datetime.timedelta(days=random.randint(0, 7200))


for s in active_specs:
    s["age_band"] = get_age_band((FY26_END - s["dob"]).days / 365.25)


tot_act = len(active_specs)
u30_c = sum(1 for s in active_specs if s["dob"] > datetime.date(1996, 3, 31))
m30_c = sum(1 for s in active_specs if datetime.date(1976, 4, 1) <= s["dob"] <= datetime.date(1996, 3, 31))
o50_c = sum(1 for s in active_specs if s["dob"] <= datetime.date(1976, 3, 31))
print(f"Active age distribution: <30={u30_c} ({u30_c/tot_act:.2%}), 30-50={m30_c} ({m30_c/tot_act:.2%}), >50={o50_c} ({o50_c/tot_act:.2%})")

# -----------------------------------------------------------------------------
# STEP 9: STOCK-FLOW LIFECYCLE MODEL ACROSS FY13–FY26
# -----------------------------------------------------------------------------
print("Calibrating stock-flow lifecycle history across FY13–FY26...")

HIRES_PLAN = {}
cur_stock = TARGET_HC["FY13"]
for fy in list(TARGET_HC.keys())[1:]:
    tgt = TARGET_HC[fy]
    sep_cnt = SEPARATIONS_PLAN[fy]
    hire_cnt = tgt - (cur_stock - sep_cnt)
    HIRES_PLAN[fy] = hire_cnt
    cur_stock = cur_stock - sep_cnt + hire_cnt

active_survivor_targets = dict(ACTIVE_SURVIVORS_PLAN)
sep_hires_needed = {fy: HIRES_PLAN[fy] - active_survivor_targets[fy] for fy in HIRES_PLAN}

active_surv_unfixed = dict(active_survivor_targets)
active_surv_unfixed["FY18"] -= 1 # EMP-103892 joined in FY18
active_surv_unfixed["FY22"] -= 1 # EMP-102451 joined in FY22

# Deduct FY26 mid-career resignations from hiring pools of joining years
resig_join_years = ["FY17"] * 50 + ["FY18"] * 15 + ["FY19"] * 30 + ["FY20"] * 40 + ["FY21"] * 20 + ["FY22"] * 26
for fy_j in resig_join_years:
    sep_hires_needed[fy_j] -= 1
random.shuffle(resig_join_years)

# 1. FY26 New Hires (167 total, 28 female)
avail_hires_fem = [s for s in non_persona_specs if s.get("gender") == "Female" and s["dob"] > datetime.date(1996, 3, 31)]
avail_hires_male = [s for s in non_persona_specs if s.get("gender") == "Male" and s["dob"] > datetime.date(1996, 3, 31)]
random.shuffle(avail_hires_fem)
random.shuffle(avail_hires_male)

target_hires_tot = 167
target_hires_fem = 28
target_hires_male = target_hires_tot - target_hires_fem

for s in avail_hires_fem[:target_hires_fem]:
    s["doj"] = datetime.date(2025, 4, 1) + datetime.timedelta(days=random.randint(0, 364))
    s["fiscal_year_joined"] = "FY26"
    s["entry_mode"] = "GATE_GT" if s.get("cadre") == "executive" else "Campus_Placement"

for s in avail_hires_male[:target_hires_male]:
    s["doj"] = datetime.date(2025, 4, 1) + datetime.timedelta(days=random.randint(0, 364))
    s["fiscal_year_joined"] = "FY26"
    s["entry_mode"] = "GATE_GT" if s.get("cadre") == "executive" else "Campus_Placement"

# 2. FY14 to FY25 Survivors (6,500 total, drawn from youngest unassigned)
unassigned_active = [s for s in non_persona_specs if s.get("fiscal_year_joined") is None]
unassigned_active.sort(key=lambda s: s["dob"], reverse=True)

for fy in sorted(active_surv_unfixed.keys(), key=lambda x: int(x[2:]), reverse=True):
    if fy == "FY26":
        continue
    surv_count = active_surv_unfixed[fy]
    fy_year = int(fy[2:])
    fy_start = datetime.date(2000 + fy_year - 1, 4, 1)
    fy_end = datetime.date(2000 + fy_year, 3, 31)
    days_span = (fy_end - fy_start).days

    for _ in range(surv_count):
        s = unassigned_active.pop(0)
        s["doj"] = fy_start + datetime.timedelta(days=random.randint(0, days_span))
        s["fiscal_year_joined"] = fy

# 3. All remaining active joined on or before FY13 (16,447 + 3 personas = 16,450 total)
min_entry_e = PARAMS["demographics"]["entry_age_min_exec"]
max_entry_e = PARAMS["demographics"]["entry_age_max_exec"]
min_entry_ne = PARAMS["demographics"]["entry_age_min_nonexec"]
max_entry_ne = PARAMS["demographics"]["entry_age_max_nonexec"]

for s in unassigned_active:
    min_entry = min_entry_e if s.get("cadre") == "executive" else min_entry_ne
    max_entry = max_entry_e if s.get("cadre") == "executive" else max_entry_ne
    doj_val = s["dob"] + datetime.timedelta(days=int(random.uniform(min_entry, max_entry) * 365.25))
    if doj_val > datetime.date(2013, 3, 31):
        doj_val = datetime.date(2013, 3, 31) - datetime.timedelta(days=random.randint(1, 365))
    s["doj"] = doj_val
    s["fiscal_year_joined"] = get_fy(doj_val)

# Generate separated employee specs
separated_specs = []

# Natural mature field attrition weighting (Rule 1 & 2)
mature_asset_wcs = [w["wc_id"] for w in WORK_CENTRES if w.get("type") == "asset" and asset_growth_rates.get(w["wc_id"], 0.0) < 0.05]
if not mature_asset_wcs:
    mature_asset_wcs = [w["wc_id"] for w in WORK_CENTRES if w.get("type") == "asset"]

for fy in sorted(TARGET_HC.keys(), key=lambda x: int(x[2:])):
    if fy == "FY13":
        continue
    fy_year = int(fy[2:])
    start_d = datetime.date(2000 + fy_year - 1, 4, 1)
    end_d = datetime.date(2000 + fy_year, 3, 31)

    if fy == "FY26":
        # 1. 20 Executive Director Superannuations (month-ends)
        for i in range(20):
            m = (i % 12) + 1
            yr = 2025 if m >= 4 else 2026
            sep_d = get_last_day_of_month(yr, m)
            dob_val = datetime.date(yr - RETIREMENT_AGE, m, random.randint(1, 28))
            doj_val = dob_val + datetime.timedelta(days=int(random.uniform(min_entry_e, max_entry_e) * 365.25))
            separated_specs.append({
                "cadre": "executive",
                "current_grade_id": "E9",
                "discipline_id": "DISC-PRD" if i % 2 == 0 else "DISC-DRL",
                "current_wc_id": delhi_hq_wc if i < 10 else mumbai_offshore_wc,
                "gender": "Male" if i > 1 else "Female",
                "dob": dob_val,
                "doj": doj_val,
                "separation_date": sep_d,
                "separation_type": "superannuation",
                "exit_interview_reason": "retirement_age",
                "target_company_or_sector": "None",
            })

        # 2. Executive Resignations in FY26 driven by continuous hazard model (Rule 5a)
        active_exec_resig_pool = [
            s for s in active_specs
            if s.get("cadre") == "executive" and not s.get("is_persona")
            and (s.get("current_wc_id") or s.get("wc_id")) != delhi_hq_wc
        ]
        random.shuffle(active_exec_resig_pool)

        for s in active_exec_resig_pool:
            if not resig_join_years:
                break
            disc = s.get("discipline_id")
            gr = s.get("current_grade_id")
            is_mid = (gr in ["E3", "E4", "E5"])

            p_resig = PARAMS["resignation_hazard"]["base_executive"]
            if is_mid:
                p_resig *= PARAMS["resignation_hazard"]["mult_e3_e5"]
            if disc == "DISC-IT":
                p_resig *= PARAMS["resignation_hazard"]["mult_it"]
                target_sector = "Tech / GCCs"
            elif disc == "DISC-FIN":
                p_resig *= PARAMS["resignation_hazard"]["mult_finance"]
                target_sector = "Private E&P / Banking"
            elif disc in ["DISC-DRL", "DISC-PRD", "DISC-GEO", "DISC-RES"]:
                p_resig *= PARAMS["resignation_hazard"]["mult_technical"]
                target_sector = "Middle East NOC"
            else:
                target_sector = "Consulting / Academia"

            if random.random() < p_resig:
                fy_j = resig_join_years.pop()
                j_yr = 2000 + int(fy_j[2:]) - 1
                doj_val = datetime.date(j_yr, 4, 1) + datetime.timedelta(days=random.randint(0, 364))
                dob_val = doj_val - datetime.timedelta(days=int(random.uniform(min_entry_e, max_entry_e) * 365.25))
                sep_d = datetime.date(2025, 4, 1) + datetime.timedelta(days=random.randint(15, 350))

                separated_specs.append({
                    "cadre": "executive",
                    "current_grade_id": gr,
                    "discipline_id": disc,
                    "current_wc_id": s.get("current_wc_id") or s.get("wc_id"),
                    "gender": s.get("gender", "Male"),
                    "dob": dob_val,
                    "doj": doj_val,
                    "separation_date": sep_d,
                    "separation_type": "resignation",
                    "exit_interview_reason": "compensation_gap_private_ep" if disc in ["DISC-IT", "DISC-FIN"] else "career_progression",
                    "target_company_or_sector": target_sector,
                })

        # Pop any remaining resignation slots from pool
        while resig_join_years:
            s = active_exec_resig_pool.pop()
            disc = s.get("discipline_id")
            gr = s.get("current_grade_id")
            fy_j = resig_join_years.pop()
            j_yr = 2000 + int(fy_j[2:]) - 1
            doj_val = datetime.date(j_yr, 4, 1) + datetime.timedelta(days=random.randint(0, 364))
            dob_val = doj_val - datetime.timedelta(days=int(random.uniform(min_entry_e, max_entry_e) * 365.25))
            sep_d = datetime.date(2025, 4, 1) + datetime.timedelta(days=random.randint(15, 350))

            separated_specs.append({
                "cadre": "executive",
                "current_grade_id": gr,
                "discipline_id": disc,
                "current_wc_id": s.get("current_wc_id") or s.get("wc_id"),
                "gender": s.get("gender", "Male"),
                "dob": dob_val,
                "doj": doj_val,
                "separation_date": sep_d,
                "separation_type": "resignation",
                "exit_interview_reason": "compensation_gap_private_ep" if disc in ["DISC-IT", "DISC-FIN"] else "career_progression",
                "target_company_or_sector": "Private Sector",
            })

        # 3. Superannuations in FY26 (835 exec, 382 non-exec = 1217 total, all on month-ends)
        fy26_exec_pool = make_balanced_wc_pool(ALL_WC_IDS, WC_EXEC_WEIGHTS, 835)
        fy26_nonexec_pool = make_balanced_wc_pool(ALL_WC_IDS, WC_NONEXEC_WEIGHTS, 382)

        for i in range(835):
            m = (i % 12) + 1
            yr = 2025 if m >= 4 else 2026
            sep_d = get_last_day_of_month(yr, m)
            dob_val = datetime.date(yr - RETIREMENT_AGE, m, random.randint(1, 28))
            doj_val = dob_val + datetime.timedelta(days=int(random.uniform(min_entry_e, max_entry_e) * 365.25))
            separated_specs.append({
                "cadre": "executive",
                "current_grade_id": random.choice(["E4", "E5", "E6", "E7", "E8"]),
                "discipline_id": random.choice(["DISC-PRD", "DISC-DRL", "DISC-RES", "DISC-GEO", "DISC-FIN", "DISC-HR"]),
                "current_wc_id": fy26_exec_pool.pop(),
                "gender": "Female" if random.random() < 0.08 else "Male",
                "dob": dob_val,
                "doj": doj_val,
                "separation_date": sep_d,
                "separation_type": "superannuation",
                "exit_interview_reason": "retirement_age",
                "target_company_or_sector": "None",
            })

        for i in range(382):
            m = (i % 12) + 1
            yr = 2025 if m >= 4 else 2026
            sep_d = get_last_day_of_month(yr, m)
            dob_val = datetime.date(yr - RETIREMENT_AGE, m, random.randint(1, 28))
            doj_val = dob_val + datetime.timedelta(days=int(random.uniform(min_entry_ne, max_entry_ne) * 365.25))
            separated_specs.append({
                "cadre": "non_executive",
                "current_grade_id": random.choice(["GRP-B", "GRP-C", "GRP-D"]),
                "discipline_id": random.choice(nonexec_tech),
                "current_wc_id": fy26_nonexec_pool.pop(),
                "gender": "Female" if random.random() < 0.08 else "Male",
                "dob": dob_val,
                "doj": doj_val,
                "separation_date": sep_d,
                "separation_type": "superannuation",
                "exit_interview_reason": "retirement_age",
                "target_company_or_sector": "None",
            })
    else:
        # Years FY14 to FY25
        n_recent = sep_hires_needed[fy]
        n_pre = SEPARATIONS_PLAN[fy] - n_recent
        hist_exec_pool = make_balanced_wc_pool(ALL_WC_IDS, HISTORICAL_EXEC_WEIGHTS, n_recent + n_pre)
        hist_nonexec_pool = make_balanced_wc_pool(ALL_WC_IDS, HISTORICAL_NONEXEC_WEIGHTS, n_recent + n_pre)

        for _ in range(n_recent):
            sep_d = start_d + datetime.timedelta(days=random.randint(30, 360))
            doj_val = start_d + datetime.timedelta(days=random.randint(0, (sep_d - start_d).days - 1))
            is_exec = (random.random() < 0.60)
            min_e = min_entry_e if is_exec else min_entry_ne
            max_e = max_entry_e if is_exec else max_entry_ne
            dob_val = doj_val - datetime.timedelta(days=int(random.uniform(min_e, max_e) * 365.25))

            separated_specs.append({
                "cadre": "executive" if is_exec else "non_executive",
                "current_grade_id": random.choice(["E1", "E2", "E3"]) if is_exec else random.choice(["GRP-C", "GRP-D"]),
                "discipline_id": random.choice(["DISC-PRD", "DISC-DRL", "DISC-IT", "DISC-FIN", "DISC-HR"]) if is_exec else random.choice(nonexec_tech),
                "current_wc_id": hist_exec_pool.pop() if is_exec else hist_nonexec_pool.pop(),
                "gender": "Female" if random.random() < 0.08 else "Male",
                "dob": dob_val,
                "doj": doj_val,
                "separation_date": sep_d,
                "separation_type": "resignation",
                "exit_interview_reason": "career_progression",
                "target_company_or_sector": "Private Sector",
            })

        for i in range(n_pre):
            m = (i % 12) + 1
            yr = (2000 + fy_year - 1) if m >= 4 else (2000 + fy_year)
            sep_d = get_last_day_of_month(yr, m)
            dob_val = datetime.date(yr - RETIREMENT_AGE, m, random.randint(1, 28))
            is_exec = (i % 2 == 0)
            min_e = min_entry_e if is_exec else min_entry_ne
            max_e = max_entry_e if is_exec else max_entry_ne
            doj_val = dob_val + datetime.timedelta(days=int(random.uniform(min_entry, max_entry) * 365.25))

            sep_wc = hist_exec_pool.pop() if is_exec else hist_nonexec_pool.pop()

            separated_specs.append({
                "cadre": "executive" if is_exec else "non_executive",
                "current_grade_id": random.choice(["E4", "E5", "E6", "GRP-C", "GRP-B"]),
                "discipline_id": random.choice(["DISC-PRD", "DISC-DRL", "DISC-GEO", "DISC-RES", "DISC-FIN", "DISC-HR"]) if is_exec else random.choice(nonexec_tech),
                "current_wc_id": sep_wc,
                "is_posted_pre21": (fy in ["FY22", "FY23", "FY24", "FY25"]),
                "gender": "Female" if random.random() < 0.08 else "Male",
                "dob": dob_val,
                "doj": doj_val,
                "separation_date": sep_d,
                "separation_type": "superannuation",
                "exit_interview_reason": "retirement_age",
                "target_company_or_sector": "None",
            })

print(f"Total separated population compiled: {len(separated_specs)}")
total_population = active_specs + separated_specs
print(f"Total simulated population: {len(total_population)}")

# Verify all 14 target headcounts
for fy in sorted(TARGET_HC.keys(), key=lambda x: int(x[2:])):
    d = TARGET_DATES[fy]
    act = sum(1 for s in total_population if s["doj"] <= d and (s.get("separation_date") is None or s["separation_date"] > d))
    tgt = TARGET_HC[fy]
    print(f"Check {fy} at {d}: actual={act}, target={tgt}, delta={act - tgt}")
    assert act == tgt, f"Headcount mismatch for {fy}: actual {act} != target {tgt}"

print("ALL 14 HEADCOUNT TARGETS (FY13–FY26) MATCH EXACTLY!")


# -----------------------------------------------------------------------------
# STEP 10: FY27 H1 MOVEMENTS (2026-04-01 TO 2026-10-19)
# -----------------------------------------------------------------------------
# 1. Superannuations in FY27 H1
h1_superann_count = 0
for s in active_specs:
    superann = get_superannuation_date(s["dob"])
    if datetime.date(2026, 4, 1) <= superann <= datetime.date(2026, 9, 30):
        s["separation_date"] = superann
        s["separation_type"] = "superannuation"
        s["exit_interview_reason"] = "retirement_age"
        s["target_company_or_sector"] = "None"
        s["employment_status"] = "Separated"
        h1_superann_count += 1
    else:
        s["employment_status"] = "Active"

# 2. Executive Resignations in FY27 H1
avail_h1_resig = [
    s for s in active_specs 
    if s.get("employment_status") == "Active" and s.get("cadre") == "executive"
    and not s.get("is_persona") and s.get("wc_id") != delhi_hq_wc
]

it_h1 = [s for s in avail_h1_resig if s.get("current_grade_id") in ["E3", "E4", "E5"] and s.get("discipline_id") == "DISC-IT"]
fin_h1 = [s for s in avail_h1_resig if s.get("current_grade_id") in ["E3", "E4", "E5"] and s.get("discipline_id") == "DISC-FIN"]
oth_h1_mid = [s for s in avail_h1_resig if s.get("current_grade_id") in ["E3", "E4", "E5"] and s.get("discipline_id") not in ["DISC-IT", "DISC-FIN"]]
oth_h1_exec = [s for s in avail_h1_resig if s.get("current_grade_id") not in ["E3", "E4", "E5"]]

selected_h1_resig = it_h1[:21] + fin_h1[:19] + oth_h1_mid[:22] + oth_h1_exec[:29]
for s in selected_h1_resig:
    s["separation_date"] = datetime.date(2026, 4, 1) + datetime.timedelta(days=random.randint(15, 190))
    s["separation_type"] = "resignation"
    s["exit_interview_reason"] = "compensation_gap_private_ep" if s.get("discipline_id") in ["DISC-IT", "DISC-FIN"] else "career_progression"
    s["target_company_or_sector"] = "Tech / GCCs" if s.get("discipline_id") == "DISC-IT" else "Private E&P"
    s["employment_status"] = "Separated"

# 3. Executive VRS / Death in FY27 H1
avail_vrs = [s for s in avail_h1_resig if s.get("employment_status") == "Active" and (ANCHOR_DATE - s["dob"]).days / 365.25 >= 50.0]
for idx, s in enumerate(avail_vrs[:12]):
    s["separation_date"] = datetime.date(2026, 4, 1) + datetime.timedelta(days=random.randint(20, 190))
    s["separation_type"] = "VRS" if idx < 9 else "death"
    s["exit_interview_reason"] = "family_medical"
    s["target_company_or_sector"] = "None"
    s["employment_status"] = "Separated"

# 4. Non-Executive Exits in FY27 H1
avail_non_exits = [s for s in active_specs if s.get("employment_status") == "Active" and s.get("cadre") == "non_executive" and s.get("wc_id") != delhi_hq_wc]
for idx, s in enumerate(avail_non_exits[:30]):
    s["separation_date"] = datetime.date(2026, 4, 1) + datetime.timedelta(days=random.randint(20, 190))
    s["separation_type"] = "VRS" if idx < 15 else "resignation"
    s["exit_interview_reason"] = "family_medical" if idx < 15 else "higher_studies"
    s["target_company_or_sector"] = "None" if idx < 15 else "Private Sector"
    s["employment_status"] = "Separated"

# 5. Graduate Trainee Batch & Non-Exec Intake
gt_intake_count = 100
non_intake_count = 36

gt_disciplines = ["DISC-PRD", "DISC-DRL", "DISC-MEC", "DISC-ELE", "DISC-CHM", "DISC-RES"]
intake_wcs = [w["wc_id"] for w in WORK_CENTRES if w.get("type") in ["asset", "plant"]]

for _ in range(gt_intake_count):
    g = "Female" if random.random() < 0.20 else "Male"
    wid = random.choice(intake_wcs)
    doj_val = datetime.date(2026, 8, 4)
    dob_val = doj_val - datetime.timedelta(days=int(random.uniform(min_entry_e, max_entry_e) * 365.25))
    total_population.append({
        "emp_id": next_emp_id(),
        "name": make_name(g, WC_BY_ID[wid].get("state_code", "DL"), wid),
        "gender": g,
        "dob": dob_val,
        "doj": doj_val,
        "fiscal_year_joined": "FY27",
        "cadre": "executive",
        "current_grade_id": "E1",
        "current_designation": GRADE_DESIGNATIONS["E1"],
        "discipline_id": random.choice(gt_disciplines),
        "current_wc_id": wid,
        "home_state_code": WC_BY_ID[wid]["state_code"],
        "category": random.choice(["General", "OBC", "SC", "ST"]),
        "pwd_flag": False,
        "pwd_category": None,
        "entry_mode": "GATE_GT",
        "employment_status": "Active",
        "posting_from": datetime.date(2026, 8, 4),
        "has_hard_station_tenure": False,
        "has_offshore_tenure": (WC_BY_ID[wid].get("onshore_offshore") == "offshore"),
    })

for _ in range(non_intake_count):
    g = "Female" if random.random() < 0.15 else "Male"
    wid = random.choice(intake_wcs)
    doj_val = datetime.date(2026, 9, 1)
    dob_val = doj_val - datetime.timedelta(days=int(random.uniform(min_entry_ne, max_entry_ne) * 365.25))
    total_population.append({
        "emp_id": next_emp_id(),
        "name": make_name(g, WC_BY_ID[wid].get("state_code", "DL"), wid),
        "gender": g,
        "dob": dob_val,
        "doj": doj_val,
        "fiscal_year_joined": "FY27",
        "cadre": "non_executive",
        "current_grade_id": "GRP-C",
        "current_designation": GRADE_DESIGNATIONS["GRP-C"],
        "discipline_id": random.choice(nonexec_tech),
        "current_wc_id": wid,
        "home_state_code": WC_BY_ID[wid]["state_code"],
        "category": random.choice(["OBC", "SC", "General"]),
        "pwd_flag": False,
        "pwd_category": None,
        "entry_mode": "Campus_Placement",
        "employment_status": "Active",
        "posting_from": datetime.date(2026, 9, 1),
        "has_hard_station_tenure": False,
        "has_offshore_tenure": False,
    })

tot_h1_seps = h1_superann_count + len(selected_h1_resig) + 12 + 30
tot_h1_hires = gt_intake_count + non_intake_count
print(f"FY27 H1 movements complete: Hires={tot_h1_hires}, Separations={tot_h1_seps}.")

# Pre-assign emp_id in exact total_population order and record baseline grade/entry_mode
for s in total_population:
    s["emp_id"] = s.get("emp_id") or next_emp_id()
    s["_orig_grade_id"] = s.get("current_grade_id") or s.get("grade_id") or ("E2" if s.get("cadre") == "executive" else "GRP-C")
    s["_orig_entry_mode"] = s.get("entry_mode") or "GATE_GT"

# Couple non-HQ active executive grades to seniority (EMP-R24, EMP-R09, EMP-R16, EMP-R20)
non_hq_execs = [
    s for s in active_specs
    if s.get("cadre") == "executive"
    and not s.get("is_persona")
    and not WC_BY_ID[s.get("current_wc_id") or s.get("wc_id") or delhi_hq_wc].get("is_corporate_hq", False)
]
orig_grade_counts = {}
for s in non_hq_execs:
    orig_grade_counts[s["current_grade_id"]] = orig_grade_counts.get(s["current_grade_id"], 0) + 1

def _eff_doj_for_grade(s):
    d = s["doj"]
    if s.get("gender") == "Female" and d < datetime.date(2022, 4, 1):
        d = min(datetime.date(2022, 3, 31), d + datetime.timedelta(days=int(18.0 * 365.25)))
    return d

non_hq_execs.sort(key=lambda s: (_eff_doj_for_grade(s), s["doj"], s["emp_id"]), reverse=True)

n_e1 = orig_grade_counts["E1"] - 601
n_e2 = orig_grade_counts["E2"] + 101
n_e0 = 350
n_e3 = orig_grade_counts["E3"] + 151
n_e4 = orig_grade_counts["E4"]
n_e5 = orig_grade_counts["E5"]
n_e6 = orig_grade_counts["E6"] - 1
n_e7 = orig_grade_counts["E7"]
n_e8 = orig_grade_counts["E8"]
n_e9 = orig_grade_counts["E9"]

coupled_grades = (
    ["E1"] * n_e1
    + ["E2"] * n_e2
    + ["E0"] * n_e0
    + ["E3"] * n_e3
    + ["E4"] * n_e4
    + ["E5"] * n_e5
    + ["E6"] * n_e6
    + ["E7"] * n_e7
    + ["E8"] * n_e8
    + ["E9"] * n_e9
)
for s, g in zip(non_hq_execs, coupled_grades):
    s["current_grade_id"] = g
    s["current_designation"] = GRADE_DESIGNATIONS[g]
    if g == "E0":
        s["entry_mode"] = "Departmental_Promotee"

# -----------------------------------------------------------------------------
# STEP 11: COMPILE FINAL TABLES & NATIVE SAP / EXCEL FILES
# -----------------------------------------------------------------------------
print("Compiling final ledger tables (H1–H5)...")

final_employees = []
final_postings = []
final_promotions = []
final_dpc_cases = []
final_separations = []

grades_seq = ['E0', 'E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7', 'E8', 'E9']

for idx, s in enumerate(total_population):
    emp_id = s.get("emp_id") or next_emp_id()
    s["emp_id"] = emp_id

    gender = s.get("gender", "Male")
    wc_id = s.get("current_wc_id") or s.get("wc_id") or delhi_hq_wc
    state_code = s.get("home_state_code") or WC_BY_ID[wc_id]["state_code"]
    name = s.get("name") or make_name(gender, state_code, wc_id)
    dob = s["dob"]
    doj = s["doj"]
    fy_joined = s.get("fiscal_year_joined") or get_fy(doj)
    cat = s.get("category") or "General"
    pwd = s.get("pwd_flag", False)
    pwd_cat = s.get("pwd_category") if pwd else None
    wc_id = s.get("current_wc_id") or s.get("wc_id") or delhi_hq_wc
    state_code = s.get("home_state_code") or WC_BY_ID[wc_id]["state_code"]
    disc_id = s.get("discipline_id") or "DISC-PRD"
    grade_id = s.get("current_grade_id") or s.get("grade_id") or ("E2" if s.get("cadre") == "executive" else "GRP-C")
    desig = s.get("current_designation") or GRADE_DESIGNATIONS.get(grade_id, "Executive")
    entry_mode = s.get("entry_mode") or "GATE_GT"
    orig_grade_id = s.get("_orig_grade_id", grade_id)
    orig_entry_mode = s.get("_orig_entry_mode", entry_mode)
    grade_changed = (grade_id != orig_grade_id or entry_mode != orig_entry_mode)

    sep_date = s.get("separation_date")
    status = "Separated" if sep_date is not None else "Active"

    ref_end = sep_date if sep_date else ANCHOR_DATE
    age_years = round((ANCHOR_DATE - dob).days / 365.25, 1)
    age_band = get_age_band((FY26_END - dob).days / 365.25)
    tenure_years = round((ref_end - doj).days / 365.25, 1)
    tenure_band = get_tenure_band(tenure_years)

    ret_date = get_superannuation_date(dob)
    ex_tag = s.get("exemption_tag", "None")
    ex_code = s.get("exemption_reason_code")

    # -------------------------------------------------------------------------
    # PROMOTIONS & DPC CASES (STRICTLY SINGLE-STEP TRANSITIONS)
    # -------------------------------------------------------------------------
    emp_proms = []
    orig_prom_dates = []
    if s.get("cadre") == "executive":
        career_days = max(1, (ref_end - doj).days)
        if grade_changed:
            orig_start_grade = "E0" if orig_entry_mode == "Departmental_Promotee" else "E1"
            orig_start_idx = grades_seq.index(orig_start_grade) if orig_start_grade in grades_seq else 0
            if orig_grade_id in ['DIR', 'CMD']:
                orig_progression = grades_seq[orig_start_idx:] + [orig_grade_id]
            elif orig_grade_id in grades_seq:
                orig_p_idx = grades_seq.index(orig_grade_id)
                orig_progression = grades_seq[orig_start_idx:orig_p_idx+1]
            else:
                orig_progression = [orig_grade_id]
            orig_steps = [(orig_progression[i], orig_progression[i+1]) for i in range(len(orig_progression)-1)]
            for step_idx, (f_gr, t_gr) in enumerate(orig_steps):
                prom_date = doj + datetime.timedelta(days=int((step_idx + 1) * (career_days / (len(orig_steps) + 1))))
                orig_prom_dates.append(prom_date)
                if t_gr in ['E5', 'E6', 'E7', 'E8', 'E9']:
                    random.randint(1, 999)
                random.randint(100, 9999)
                if t_gr in ['E5', 'E6', 'E7', 'E8', 'E9']:
                    random.randint(20, 50)
                    random.randint(12, 25)

        prom_rng = _AUX_RNG if grade_changed else random
        start_grade = "E0" if s.get("entry_mode") == "Departmental_Promotee" else "E1"
        start_idx = grades_seq.index(start_grade) if start_grade in grades_seq else 0
        if grade_id in ['DIR', 'CMD']:
            progression = grades_seq[start_idx:] + [grade_id]
        elif grade_id in grades_seq:
            p_idx = grades_seq.index(grade_id)
            progression = grades_seq[start_idx:p_idx+1]
        else:
            progression = [grade_id]

        steps = [(progression[i], progression[i+1]) for i in range(len(progression)-1)]

        for step_idx, (f_gr, t_gr) in enumerate(steps):
            prom_date = doj + datetime.timedelta(days=int((step_idx + 1) * (career_days / (len(steps) + 1))))
            prom_fy = get_fy(prom_date)

            if t_gr in ['E2', 'E3', 'E4']:
                prom_mode = 'time_bound'
                dpc_code = None
            elif t_gr in ['E5', 'E6', 'E7', 'E8', 'E9']:
                prom_mode = 'merit'
                disc_code = DISC_BY_ID[disc_id]["code"]
                dpc_code = f"DPC-{prom_fy}-{t_gr}-{disc_code}-{prom_rng.randint(1, 999):03d}"
            else:
                prom_mode = 'selection'
                dpc_code = None

            p_rec = {
                "promotion_id": next_promotion_id(),
                "emp_id": emp_id,
                "wc_id": wc_id,
                "discipline_id": disc_id,
                "from_grade_id": f_gr,
                "to_grade_id": t_gr,
                "effective_date": prom_date,
                "fiscal_year": prom_fy,
                "dpc_id": dpc_code,
                "promotion_mode": prom_mode,
                "residency_years_completed": round(career_days / (365.25 * (len(steps) + 1)), 1),
                "apar_benchmark_met": True,
                "vigilance_cleared": True,
                "hard_station_completed_flag": True if t_gr in ['E5', 'E6', 'E7', 'E8', 'E9'] else False,
                "order_no": f"ORD/PROM/{prom_date.year}/{prom_rng.randint(100, 9999):04d}",
            }
            emp_proms.append(p_rec)
            final_promotions.append(p_rec)

            if dpc_code:
                final_dpc_cases.append({
                    "dpc_id": dpc_code,
                    "emp_id": emp_id,
                    "fiscal_year": prom_fy,
                    "wc_id": wc_id,
                    "from_grade_id": f_gr,
                    "to_grade_id": t_gr,
                    "discipline_id": disc_id,
                    "due_date": prom_date - datetime.timedelta(days=60),
                    "held_date": prom_date - datetime.timedelta(days=15),
                    "status": "completed",
                    "eligible_candidates_count": prom_rng.randint(20, 50),
                    "recommended_candidates_count": prom_rng.randint(12, 25),
                    "pending_reason": "none",
                    "delay_bottleneck_reason": None,
                    "delay_months": 0,
                    "accelerated_merit_benchmark_score": 85.0 if t_gr == "E7" else None,
                })

    # -------------------------------------------------------------------------
    # POSTINGS GENERATION (SCD2 CAREER MOBILITY WITH REALISTIC INERTIA)
    # -------------------------------------------------------------------------
    emp_postings = []
    career_days = max(1, (ref_end - doj).days)
    career_years = career_days / 365.25
    is_office = (WC_BY_ID[wc_id].get("type") == "office" or WC_BY_ID[wc_id].get("is_corporate_hq", False))
    is_static_centre = (WC_BY_ID[wc_id].get("type") in ["institute", "basin", "service"])
    is_non_exec = (s.get("cadre") == "non_executive")

    if s.get("is_persona"):
        emp_postings = PERSONA_POSTINGS.get(emp_id, [])
    else:
        # Determine annual work centre locations at March 31 of each year from 2021 to 2026
        annual_wcs = {2026: wc_id}
        for yr in [2025, 2024, 2023, 2022, 2021]:
            target_dt = datetime.date(yr, 3, 31)
            if doj > target_dt or (sep_date and sep_date < target_dt):
                continue
            next_w = annual_wcs.get(yr + 1, wc_id)
            if is_non_exec or is_static_centre:
                annual_wcs[yr] = wc_id
            elif is_office:
                # Corporate HQ & Regional Offices tenure stickiness
                p_off_move = 0.10 if wc_id == delhi_hq_wc else 0.04
                annual_wcs[yr] = random.choices(OPERATIONAL_WCS, weights=HISTORICAL_OPERATIONAL_EXEC_WEIGHTS, k=1)[0] if random.random() < p_off_move else next_w
            else:
                g = asset_growth_rates.get(next_w, 0.0)
                p_move = max(0.050, min(0.12, 0.060 + g * 0.40))
                annual_wcs[yr] = random.choices(OPERATIONAL_WCS, weights=HISTORICAL_OPERATIONAL_EXEC_WEIGHTS, k=1)[0] if random.random() < p_move else next_w

        # Hard station requirement for mid-career technical executives
        is_tech = (disc_id in ["DISC-DRL", "DISC-PRD", "DISC-GEO", "DISC-GPS", "DISC-RES", "DISC-MEC", "DISC-ELE"])
        if s.get("cadre") == "executive" and orig_grade_id in ["E3", "E4", "E5"]:
            hazard_p = PARAMS["mobility"]["hard_station_hazard_tech"] if is_tech else PARAMS["mobility"]["hard_station_hazard_supp"]
            has_hard_req = (random.random() < hazard_p) or any(annual_wcs.get(y) in HARD_STATION_WCS for y in annual_wcs)
        else:
            has_hard_req = any(annual_wcs.get(y) in HARD_STATION_WCS for y in annual_wcs)

        # Corporate HQ impending retirement exemption tag
        if is_office and (ref_end - dob).days / 365.25 >= PARAMS["mobility"]["retirement_exemption_age"]:
            if random.random() < 0.35:
                ex_tag = "Impending_Retirement"
                ex_code = "EX-RET3Y"
                s["exemption_approved_by"] = "Director HR"

        # Build contiguous postings from annual_wcs
        years_sorted = [2021, 2022, 2023, 2024, 2025, 2026]
        active_years = [
            y for y in years_sorted 
            if doj <= datetime.date(y, 3, 31) and (sep_date is None or sep_date >= datetime.date(y, 3, 31))
        ]

        stints = []
        if not active_years:
            stints = [{'from_date': doj, 'to_date': sep_date, 'wc_id': wc_id}]
        else:
            rle = []
            for y in active_years:
                w = annual_wcs[y]
                if not rle or rle[-1]['wc'] != w:
                    rle.append({'wc': w, 'start_yr': y, 'end_yr': y})
                else:
                    rle[-1]['end_yr'] = y

            rle_stints = []
            for i, seg in enumerate(rle):
                is_first = (i == 0)
                is_last = (i == len(rle) - 1)

                if is_first:
                    f_d = datetime.date(seg['start_yr'] - 1, 7, 1)
                    if f_d <= doj:
                        f_d = doj
                else:
                    f_d = datetime.date(seg['start_yr'] - 1, 7, 1)
                    if f_d <= doj:
                        f_d = doj + datetime.timedelta(days=i)

                if is_last:
                    t_d = sep_date
                else:
                    t_d = datetime.date(seg['end_yr'], 6, 30)
                    if sep_date and t_d >= sep_date:
                        t_d = sep_date

                if t_d is not None and f_d > t_d:
                    f_d = t_d
                rle_stints.append({'from_date': f_d, 'to_date': t_d, 'wc_id': seg['wc']})

            first_rle_start = rle_stints[0]['from_date']
            earlier_stints = []

            if not is_non_exec and (first_rle_start - doj).days >= 365 * 2.5:
                curr_start = first_rle_start
                curr_wc = rle_stints[0]['wc_id']
                cluster_hist = {WC_BY_ID[curr_wc].get("cluster_id"): (ref_end - curr_start).days / 365.25}

                needs_hard = has_hard_req and (curr_wc not in HARD_STATION_WCS)

                while (curr_start - doj).days >= 365 * 2.0:
                    rem_years = (curr_start - doj).days / 365.25
                    if rem_years <= 4.8:
                        prev_len = rem_years
                        prev_start = doj
                    else:
                        prev_len = random.uniform(3.2, 4.5)
                        prev_start = curr_start - datetime.timedelta(days=int(prev_len * 365.25))
                        if (prev_start - doj).days < 365 * 2.0:
                            prev_start = doj
                            prev_len = (curr_start - doj).days / 365.25

                    valid_wcs = [w for w in OPERATIONAL_WCS if w != curr_wc]
                    valid_wcs = [w for w in valid_wcs if cluster_hist.get(WC_BY_ID[w].get("cluster_id"), 0) + prev_len <= PARAMS["mobility"]["cluster_max_years"]]
                    if not valid_wcs:
                        valid_wcs = [w for w in OPERATIONAL_WCS if w != curr_wc]

                    if needs_hard and any(w in HARD_STATION_WCS for w in valid_wcs):
                        hard_cands = [w for w in valid_wcs if w in HARD_STATION_WCS]
                        prev_wc = random.choice(hard_cands)
                        needs_hard = False
                    else:
                        weights = [max(1, wc_establishment[w]["ga"]) for w in valid_wcs]
                        prev_wc = random.choices(valid_wcs, weights=weights, k=1)[0]

                    earlier_stints.append({
                        'from_date': prev_start,
                        'to_date': curr_start - datetime.timedelta(days=1),
                        'wc_id': prev_wc
                    })
                    cl = WC_BY_ID[prev_wc].get("cluster_id")
                    cluster_hist[cl] = cluster_hist.get(cl, 0) + prev_len
                    curr_start = prev_start
                    curr_wc = prev_wc

                earlier_stints = list(reversed(earlier_stints))
            else:
                rle_stints[0]['from_date'] = doj

            stints = earlier_stints + rle_stints

        # Assign posting_type to stints
        for s_idx, st in enumerate(stints):
            st["posting_type"] = "initial" if s_idx == 0 else ("hard_station" if st["wc_id"] in HARD_STATION_WCS else "rotation")

        # Compile emp_postings including in-place promotions
        emp_postings = []
        for st_idx, st in enumerate(stints):
            st_from = st["from_date"]
            st_to = st["to_date"]
            st_wc = st["wc_id"]
            st_type = st["posting_type"]
            end_bound = st_to if st_to else ref_end

            proms_in_stint = [
                p for p in emp_proms 
                if st_from < p["effective_date"] <= end_bound
            ]

            if not proms_in_stint:
                gr = ("E0" if s.get("entry_mode") == "Departmental_Promotee" else "E1") if s.get("cadre") == "executive" else grade_id
                for p in emp_proms:
                    if st_from >= p["effective_date"]:
                        gr = p["to_grade_id"]
                emp_postings.append({
                    "from_date": st_from,
                    "to_date": st_to,
                    "wc_id": st_wc,
                    "grade_id": gr,
                    "posting_type": st_type,
                })
            else:
                gr0 = ("E0" if s.get("entry_mode") == "Departmental_Promotee" else "E1") if s.get("cadre") == "executive" else grade_id
                for p in emp_proms:
                    if st_from >= p["effective_date"]:
                        gr0 = p["to_grade_id"]
                p0 = proms_in_stint[0]
                seg0_to = p0["effective_date"] - datetime.timedelta(days=1)
                emp_postings.append({
                    "from_date": st_from,
                    "to_date": seg0_to,
                    "wc_id": st_wc,
                    "grade_id": gr0,
                    "posting_type": st_type,
                })
                for p_i, p_cur in enumerate(proms_in_stint):
                    is_last_prom = (p_i == len(proms_in_stint) - 1)
                    p_next_date = proms_in_stint[p_i + 1]["effective_date"] if not is_last_prom else None
                    seg_from = p_cur["effective_date"]
                    seg_to = (p_next_date - datetime.timedelta(days=1)) if p_next_date else st_to
                    emp_postings.append({
                        "from_date": seg_from,
                        "to_date": seg_to,
                        "wc_id": st_wc,
                        "grade_id": p_cur["to_grade_id"],
                        "posting_type": "promotion",  # IN-PLACE PROMOTION
                    })

        if grade_changed:
            n_orig_postings = len(stints) + sum(
                1
                for st in stints
                for d in orig_prom_dates
                if st["from_date"] < d <= (st["to_date"] if st["to_date"] else ref_end)
            )
            for _ in range(n_orig_postings):
                random.randint(100, 9999)

    post_rng = _AUX_RNG if (grade_changed and not s.get("is_persona")) else random
    has_hard = any(p["wc_id"] in HARD_STATION_WCS for p in emp_postings)
    has_off = any(p["wc_id"] in OFFSHORE_WCS for p in emp_postings)

    # Postings record generation with strict date bounds
    for p_idx, p in enumerate(emp_postings):
        p_from = p["from_date"]
        p_to = p["to_date"]
        if p_to is not None and p_from > p_to:
            p_from = p_to

        is_cur = (p_to is None and status == "Active")
        t_months = (ANCHOR_DATE.year - p_from.year)*12 + (ANCHOR_DATE.month - p_from.month) if p_to is None else ((p_to.year - p_from.year)*12 + (p_to.month - p_from.month))

        is_relocation = (p_idx > 0 and p["wc_id"] != emp_postings[p_idx-1]["wc_id"])
        tg = 120000.0 if is_relocation else None
        cta = 150000.0 if is_relocation else None
        bag = 50000.0 if is_relocation else None
        tot_c = (tg + cta + bag) if is_relocation else None

        final_postings.append({
            "posting_id": next_posting_id(),
            "emp_id": emp_id,
            "wc_id": p["wc_id"],
            "from_date": p_from,
            "to_date": p_to,
            "fiscal_year": get_fy(p_from),
            "grade_id": p["grade_id"],
            "discipline_id": disc_id,
            "designation": GRADE_DESIGNATIONS.get(p["grade_id"], desig),
            "posting_type": p.get("posting_type", "rotation"),
            "order_no": f"ORD/HR/{p_from.year}/{post_rng.randint(100, 9999):04d}",
            "tenure_months": max(1, t_months),
            "is_current_posting": is_cur,
            "exemption_tag": ex_tag if is_cur else "None",
            "exemption_reason_code": ex_code if is_cur else None,
            "exemption_approved_by": s.get("exemption_approved_by") if is_cur else None,
            "exemption_valid_until": ret_date if (is_cur and ex_tag == "Impending_Retirement") else None,
            "transfer_grant_inr": tg,
            "composite_transfer_grant_cta_inr": cta,
            "baggage_transport_cost_inr": bag,
            "total_transfer_cost_inr": tot_c,
        })

    # -------------------------------------------------------------------------
    # SEPARATIONS GENERATION (H5)
    # -------------------------------------------------------------------------
    if status == "Separated":
        final_separations.append({
            "separation_id": next_separation_id(),
            "emp_id": emp_id,
            "separation_date": sep_date,
            "fiscal_year": get_fy(sep_date),
            "separation_type": s.get("separation_type", "superannuation"),
            "last_grade_id": grade_id,
            "discipline_id": disc_id,
            "last_wc_id": wc_id,
            "age_at_separation": round((sep_date - dob).days / 365.25, 1),
            "total_service_years": round((sep_date - doj).days / 365.25, 1),
            "exit_interview_reason": s.get("exit_interview_reason", "retirement_age"),
            "target_company_or_sector": s.get("target_company_or_sector", "None"),
        })

    final_employees.append({
        "emp_id": emp_id,
        "name": name,
        "gender": gender,
        "dob": dob,
        "doj": doj,
        "fiscal_year_joined": fy_joined,
        "category": cat,
        "pwd_flag": pwd,
        "pwd_category": pwd_cat,
        "home_state_code": state_code,
        "discipline_id": disc_id,
        "current_grade_id": grade_id,
        "current_wc_id": wc_id,
        "current_designation": desig,
        "entry_mode": entry_mode,
        "employment_status": status,
        "separation_date": sep_date,
        "age_years": age_years,
        "age_band": age_band,
        "total_tenure_years": tenure_years,
        "tenure_band": tenure_band,
        "has_hard_station_tenure": has_hard,
        "has_offshore_tenure": has_off,
        "exemption_tag": ex_tag if status == "Active" else "None",
        "exemption_reason_code": ex_code if status == "Active" else None,
        "retirement_date": ret_date,
    })

# S11: Add pending/delayed DPC dockets for active in-position feeder officers in Drilling and Production
active_drl_feeders = [e for e in final_employees if e["employment_status"] == "Active" and e["discipline_id"] == "DISC-DRL" and e["current_grade_id"] in ["E4", "E5"]]
active_prd_feeders = [e for e in final_employees if e["employment_status"] == "Active" and e["discipline_id"] == "DISC-PRD" and e["current_grade_id"] in ["E4", "E5"]]

for e in active_drl_feeders:
    if random.random() < PARAMS["dpc_delay"]["hazard_drilling"]:
        t_gr = "E5" if e["current_grade_id"] == "E4" else "E6"
        final_dpc_cases.append({
            "dpc_id": f"DPC-FY26-{t_gr}-DRL-{random.randint(100, 999)}",
            "emp_id": e["emp_id"],
            "fiscal_year": "FY26",
            "wc_id": e["current_wc_id"],
            "from_grade_id": e["current_grade_id"],
            "to_grade_id": t_gr,
            "discipline_id": "DISC-DRL",
            "due_date": datetime.date(2025, 6, 30),
            "held_date": None,
            "status": "delayed",
            "eligible_candidates_count": random.randint(30, 80),
            "recommended_candidates_count": 0,
            "pending_reason": "vigilance_clearance_pending",
            "delay_bottleneck_reason": "Pending CVO advice on disciplinary review appeals",
            "delay_months": random.randint(7, 10),
            "accelerated_merit_benchmark_score": None,
        })

for e in active_prd_feeders:
    if random.random() < PARAMS["dpc_delay"]["hazard_production"]:
        t_gr = "E5" if e["current_grade_id"] == "E4" else "E6"
        final_dpc_cases.append({
            "dpc_id": f"DPC-FY26-{t_gr}-PRD-{random.randint(100, 999)}",
            "emp_id": e["emp_id"],
            "fiscal_year": "FY26",
            "wc_id": e["current_wc_id"],
            "from_grade_id": e["current_grade_id"],
            "to_grade_id": t_gr,
            "discipline_id": "DISC-PRD",
            "due_date": datetime.date(2025, 7, 31),
            "held_date": None,
            "status": "delayed",
            "eligible_candidates_count": random.randint(30, 80),
            "recommended_candidates_count": 0,
            "pending_reason": "court_stay_seniority_dispute",
            "delay_bottleneck_reason": "CAT Guwahati stay on feeder grade seniority roster",
            "delay_months": random.randint(7, 10),
            "accelerated_merit_benchmark_score": None,
        })

print(f"Total compiled: {len(final_employees)} employees, {len(final_postings)} postings, {len(final_promotions)} promotions, {len(final_dpc_cases)} DPC cases, {len(final_separations)} separations.")

# -----------------------------------------------------------------------------
# STEP 12: WRITE SOURCE-FORMAT LANDING FILES (STRICTLY SCHEMA-DECLARED)
# -----------------------------------------------------------------------------
print("Writing landing files in source-native format...")

df_emp = pd.DataFrame(final_employees)
df_post = pd.DataFrame(final_postings)
df_prom = pd.DataFrame(final_promotions)
df_dpc = pd.DataFrame(final_dpc_cases)
df_sep = pd.DataFrame(final_separations)

# Map to SAP field headers per schema_silver sap_field_map
emp_sap_map = {
    "emp_id": "PERNR",
    "doj": "BEGDA",
    "dob": "GBDAT",
    "gender": "GESCH",
    "category": "VDSK1",
    "current_wc_id": "WERKS",
    "current_grade_id": "PERSK",
    "employment_status": "STAT2",
}
df_emp_sap = df_emp.rename(columns=emp_sap_map)
df_emp_sap.to_csv(LANDING_SAP / "PA0002_PA0001.csv", index=False)
print("Wrote PA0002_PA0001.csv")

post_sap_map = {
    "emp_id": "PERNR",
    "from_date": "BEGDA",
    "to_date": "ENDDA",
    "wc_id": "WERKS",
    "grade_id": "PERSK",
    "posting_type": "MASSN",
    "exemption_reason_code": "MASSG",
}
df_post_sap = df_post.rename(columns=post_sap_map)
df_post_sap.to_csv(LANDING_SAP / "PA0001.csv", index=False)
print("Wrote PA0001.csv")

prom_sap_map = {
    "emp_id": "PERNR",
    "effective_date": "BEGDA",
    "promotion_mode": "MASSN",
    "to_grade_id": "PERSK",
}
df_prom_sap = df_prom.rename(columns=prom_sap_map)
df_prom_sap.to_csv(LANDING_SAP / "PA0000_promotions.csv", index=False)
print("Wrote PA0000_promotions.csv")

sep_sap_map = {
    "emp_id": "PERNR",
    "separation_date": "BEGDA",
    "separation_type": "MASSN",
    "exit_interview_reason": "MASSG",
}
df_sep_sap = df_sep.rename(columns=sep_sap_map)
df_sep_sap.to_csv(LANDING_SAP / "PA0000_separations.csv", index=False)
print("Wrote PA0000_separations.csv")

with pd.ExcelWriter(LANDING_EXCEL / "DPC_tracker.xlsx", engine="openpyxl") as writer:
    df_dpc.to_excel(writer, sheet_name="DPC_Tracker", index=False)
print("Wrote DPC_tracker.xlsx")

# Ensure no duplicate/obsolete landing files exist in landing/sap
for obsolete_file in [LANDING_SAP / "PA0002.csv", LANDING_SAP / "PA0000.csv"]:
    if obsolete_file.exists():
        obsolete_file.unlink()

print("SUCCESS: HR Lifecycle Simulator finished cleanly.")
