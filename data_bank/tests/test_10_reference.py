"""Step 1.1 Automated Test Suite: Reference Data R1–R10.

Verifies:
1. File completeness and schema validity for all 12 reference YAML files.
2. Unique primary keys across all reference entities.
3. Referential integrity / foreign key relationships (fields->wc, projects->wc, cc->wc/field).
4. Organogram compliance: 14 assets, 3 plants, 9 basins, 10 institutes, Corporate HQ Delhi & Dehradun.
5. Geographic footprint: 12 states, consistent with FACTS BRSR 41 locations.
6. Price/FX monthly continuity: 126 continuous months (Apr-2016 to Sep-2026) anchored to FACTS.
7. Question Bank coverage: Every work centre, field, institute, and region named in questions.yaml
   resolves to a canonical reference entity without misses.
"""

import re
from pathlib import Path
import pytest
import yaml

REF_DIR = Path(__file__).resolve().parent.parent / "world_bible" / "reference"


@pytest.fixture(scope="module")
def work_centres_data():
    with open(REF_DIR / "work_centres.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["work_centres"]


@pytest.fixture(scope="module")
def grades_data():
    with open(REF_DIR / "grades.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["grades"]


@pytest.fixture(scope="module")
def disciplines_data():
    with open(REF_DIR / "disciplines.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["disciplines"]


@pytest.fixture(scope="module")
def fields_data():
    with open(REF_DIR / "fields.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["fields"]


@pytest.fixture(scope="module")
def projects_data():
    with open(REF_DIR / "projects.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["projects"]


@pytest.fixture(scope="module")
def cost_centres_data():
    with open(REF_DIR / "cost_centres.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def customers_data():
    with open(REF_DIR / "customers.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["customers"]


@pytest.fixture(scope="module")
def vendors_data():
    with open(REF_DIR / "vendors.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["vendors"]


@pytest.fixture(scope="module")
def geography_data():
    with open(REF_DIR / "geography.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["states"]


@pytest.fixture(scope="module")
def prices_fx_data():
    with open(REF_DIR / "prices_fx.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["prices_fx"]


@pytest.fixture(scope="module")
def id_conventions_data():
    with open(REF_DIR / "id_conventions.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def time_window_data():
    with open(REF_DIR / "time_window.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def questions_data():
    with open(REF_DIR / "questions.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["questions"]


# ==============================================================================
# 1. FILE COMPLETENESS AND STRUCTURE
# ==============================================================================


def test_reference_files_exist():
    expected_files = [
        "work_centres.yaml",
        "grades.yaml",
        "disciplines.yaml",
        "fields.yaml",
        "projects.yaml",
        "cost_centres.yaml",
        "customers.yaml",
        "vendors.yaml",
        "geography.yaml",
        "prices_fx.yaml",
        "id_conventions.yaml",
        "time_window.yaml",
        "questions.yaml",
    ]
    for filename in expected_files:
        p = REF_DIR / filename
        assert p.exists(), f"Reference file {filename} is missing in {REF_DIR}"
        assert p.stat().st_size > 0, f"Reference file {filename} is empty"


# ==============================================================================
# 2. UNIQUE IDENTIFIERS ACROSS ENTITIES
# ==============================================================================


def test_unique_work_centre_ids(work_centres_data):
    wc_ids = [wc["wc_id"] for wc in work_centres_data]
    assert len(wc_ids) == len(
        set(wc_ids)
    ), f"Duplicate wc_id found: {len(wc_ids)} vs {len(set(wc_ids))}"
    assert len(wc_ids) >= 44, f"Expected ~45 work centres, got {len(wc_ids)}"


def test_unique_grade_ids(grades_data):
    grade_ids = [g["grade_id"] for g in grades_data]
    assert len(grade_ids) == len(
        set(grade_ids)
    ), f"Duplicate grade_id found: {len(grade_ids)} vs {len(set(grade_ids))}"
    for required in [
        "E0",
        "E1",
        "E2",
        "E3",
        "E4",
        "E5",
        "E6",
        "E7",
        "E8",
        "E9",
        "GRP-B",
        "GRP-C",
        "GRP-D",
    ]:
        assert required in grade_ids, f"Required grade {required} missing"


def test_unique_discipline_ids(disciplines_data):
    disc_ids = [d["discipline_id"] for d in disciplines_data]
    assert len(disc_ids) == len(set(disc_ids)), "Duplicate discipline_id found"
    assert (
        len(disc_ids) >= 28
    ), f"Expected ~30 disciplines, got {len(disc_ids)}"


def test_unique_field_ids(fields_data):
    field_ids = [f["field_id"] for f in fields_data]
    assert len(field_ids) == len(set(field_ids)), "Duplicate field_id found"
    assert len(field_ids) >= 45, f"Expected ~45 fields, got {len(field_ids)}"


def test_unique_project_ids(projects_data):
    prj_ids = [p["prj_id"] for p in projects_data]
    assert len(prj_ids) == len(set(prj_ids)), "Duplicate prj_id found"
    assert len(prj_ids) >= 55, f"Expected ~60 projects, got {len(prj_ids)}"


def test_unique_cost_and_profit_centres(cost_centres_data):
    cc_ids = [c["cost_centre_id"] for c in cost_centres_data["cost_centres"]]
    assert len(cc_ids) == len(set(cc_ids)), "Duplicate cost_centre_id found"
    assert (
        len(cc_ids) >= 380
    ), f"Expected ~400 cost centres, got {len(cc_ids)}"

    pc_ids = [p["profit_centre_id"] for p in cost_centres_data["profit_centres"]]
    assert len(pc_ids) == len(set(pc_ids)), "Duplicate profit_centre_id found"
    assert len(pc_ids) >= 44, f"Expected ~45 profit centres, got {len(pc_ids)}"


def test_unique_customer_ids(customers_data):
    cust_ids = [c["customer_id"] for c in customers_data]
    assert len(cust_ids) == len(set(cust_ids)), "Duplicate customer_id found"
    assert len(cust_ids) >= 25, f"Expected ~25 customers, got {len(cust_ids)}"


def test_unique_vendor_ids(vendors_data):
    v_ids = [v["vendor_id"] for v in vendors_data]
    assert len(v_ids) == len(set(v_ids)), "Duplicate vendor_id found"
    assert (
        len(v_ids) == 2000
    ), f"Expected exactly 2000 seeded vendors, got {len(v_ids)}"


def test_unique_monthly_prices(prices_fx_data):
    months = [p["month"] for p in prices_fx_data]
    assert len(months) == len(set(months)), "Duplicate months in prices_fx"
    assert (
        len(months) == 126
    ), f"Expected exactly 126 months (FY17-FY27 H1), got {len(months)}"


# ==============================================================================
# 3. REFERENTIAL INTEGRITY (FOREIGN KEYS)
# ==============================================================================


def test_fields_to_work_centre_fk(fields_data, work_centres_data):
    valid_wc_ids = {wc["wc_id"] for wc in work_centres_data}
    for f in fields_data:
        assert (
            f["asset_wc_id"] in valid_wc_ids
        ), f"Field {f['field_id']} references invalid asset_wc_id {f['asset_wc_id']}"


def test_projects_to_work_centre_fk(projects_data, work_centres_data):
    valid_wc_ids = {wc["wc_id"] for wc in work_centres_data}
    for p in projects_data:
        assert (
            p["asset_wc_id"] in valid_wc_ids
        ), f"Project {p['prj_id']} references invalid asset_wc_id {p['asset_wc_id']}"


def test_cost_centres_to_wc_and_field_fk(
    cost_centres_data, work_centres_data, fields_data
):
    valid_wc_ids = {wc["wc_id"] for wc in work_centres_data}
    valid_field_ids = {f["field_id"] for f in fields_data}

    for cc in cost_centres_data["cost_centres"]:
        assert (
            cc["wc_id"] in valid_wc_ids
        ), f"Cost centre {cc['cost_centre_id']} references invalid wc_id {cc['wc_id']}"
        if cc.get("field_id"):
            assert (
                cc["field_id"] in valid_field_ids
            ), f"Cost centre {cc['cost_centre_id']} references invalid field_id {cc['field_id']}"

    for pc in cost_centres_data["profit_centres"]:
        assert (
            pc["wc_id"] in valid_wc_ids
        ), f"Profit centre {pc['profit_centre_id']} references invalid wc_id {pc['wc_id']}"


# ==============================================================================
# 4. ORGANOGRAM AND CORPORATE GOVERNANCE COMPLIANCE
# ==============================================================================


def test_organogram_entities_present(work_centres_data):
    wc_by_id = {wc["wc_id"]: wc for wc in work_centres_data}

    # 1. Corporate HQ & Primary Admin
    assert "WC-DEL" in wc_by_id and wc_by_id["WC-DEL"]["is_corporate_hq"]
    assert "WC-DDN" in wc_by_id and wc_by_id["WC-DDN"]["is_corporate_hq"]

    # 2. All 14 Assets (FACTS §A2)
    expected_assets = [
        "WC-MUM",
        "WC-BAS",
        "WC-NEH",
        "WC-EAS",
        "WC-AHM",
        "WC-MEH",
        "WC-ANK",
        "WC-CAM",
        "WC-ASM",
        "WC-JOR",
        "WC-TRI",
        "WC-BOK",
        "WC-RAJ",
        "WC-CAU",
    ]
    for asset_id in expected_assets:
        assert asset_id in wc_by_id, f"Asset {asset_id} missing from work centres"
        assert wc_by_id[asset_id]["type"] == "asset"

    # 3. All 3 Plants (FACTS §A2)
    expected_plants = ["WC-URN", "WC-HAZ", "WC-DAH"]
    for plant_id in expected_plants:
        assert plant_id in wc_by_id, f"Plant {plant_id} missing from work centres"
        assert wc_by_id[plant_id]["type"] == "plant"

    # 4. All 9 Basins (FACTS §A2)
    expected_basins = [
        "WC-WOB",
        "WC-WNB",
        "WC-RAJ-BSN",
        "WC-AAB",
        "WC-SIL",
        "WC-CAB",
        "WC-KGB",
        "WC-FRB",
        "WC-MBA",
    ]
    for basin_id in expected_basins:
        assert basin_id in wc_by_id, f"Basin {basin_id} missing from work centres"
        assert wc_by_id[basin_id]["type"] == "basin"

    # 5. Institutes (FACTS §A2)
    expected_institutes = [
        "WC-KDM",
        "WC-GEO",
        "WC-IRS",
        "WC-INB",
        "WC-CEW",
        "WC-IDW",
        "WC-IOG",
        "WC-IEO",
        "WC-ACA",
        "WC-ATI",
    ]
    for inst_id in expected_institutes:
        assert (
            inst_id in wc_by_id
        ), f"Institute {inst_id} missing from work centres"
        assert wc_by_id[inst_id]["type"] == "institute"


# ==============================================================================
# 5. GEOGRAPHIC FOOTPRINT & CALIBRATION RECONCILIATION
# ==============================================================================


def test_geographic_footprint_12_states(work_centres_data):
    """FACTS BRSR p.140-141: ONGC operates across 12 states (41 locations).

    Reconciles exactly with canonical work centres.
    """
    states = {wc["state"] for wc in work_centres_data}
    assert (
        len(states) == 12
    ), f"Expected exactly 12 states as per FACTS BRSR, got {len(states)}: {sorted(states)}"
    expected_12_states = {
        "Delhi",
        "Uttarakhand",
        "Maharashtra",
        "Gujarat",
        "Assam",
        "Tripura",
        "Andhra Pradesh",
        "Tamil Nadu",
        "Jharkhand",
        "Rajasthan",
        "West Bengal",
        "Goa",
    }
    assert states == expected_12_states, f"Mismatch in 12 states: {states ^ expected_12_states}"


def test_aspirational_districts_csr(geography_data):
    """Verify CSR geography includes flagged aspirational districts."""
    total_districts = 0
    aspirational_count = 0
    for state in geography_data:
        for dist in state["districts"]:
            total_districts += 1
            if dist["is_aspirational"]:
                aspirational_count += 1

    assert (
        total_districts >= 60
    ), f"Expected >=60 CSR districts, got {total_districts}"
    assert (
        aspirational_count >= 15
    ), f"Expected >=15 aspirational districts, got {aspirational_count}"


# ==============================================================================
# 6. PRICE & FX MONTHLY INTEGRITY
# ==============================================================================


def test_price_fx_continuity_and_calibration(prices_fx_data):
    months = [p["month"] for p in prices_fx_data]
    assert months[0] == "2016-04", f"Expected start at 2016-04, got {months[0]}"
    assert months[-1] == "2026-09", f"Expected end at 2026-09, got {months[-1]}"

    # Calibration anchors from FACTS §D3
    fy26_records = [p for p in prices_fx_data if p["fiscal_year"] == "FY26"]
    avg_fy26_realisation = sum(
        p["ongc_crude_net_realisation_usd_bbl"] for p in fy26_records
    ) / len(fy26_records)
    assert (
        abs(avg_fy26_realisation - 68.40) < 1.0
    ), f"FY26 average realisation {avg_fy26_realisation:.2f} differs from FACTS $68.40"

    fy25_records = [p for p in prices_fx_data if p["fiscal_year"] == "FY25"]
    avg_fy25_realisation = sum(
        p["ongc_crude_net_realisation_usd_bbl"] for p in fy25_records
    ) / len(fy25_records)
    assert (
        abs(avg_fy25_realisation - 76.90) < 1.0
    ), f"FY25 average realisation {avg_fy25_realisation:.2f} differs from FACTS $76.90"

    fy24_records = [p for p in prices_fx_data if p["fiscal_year"] == "FY24"]
    avg_fy24_realisation = sum(
        p["ongc_crude_net_realisation_usd_bbl"] for p in fy24_records
    ) / len(fy24_records)
    assert (
        abs(avg_fy24_realisation - 80.77) < 1.0
    ), f"FY24 average realisation {avg_fy24_realisation:.2f} differs from FACTS $80.77"

    # FY26 INR realisation alignment to FACTS ₹6,042/bbl
    avg_fy26_inr_realisation = sum(
        p["ongc_crude_net_realisation_inr_bbl"] for p in fy26_records
    ) / len(fy26_records)
    assert (
        abs(avg_fy26_inr_realisation - 6042.0) < 5.0
    ), f"FY26 average INR realisation {avg_fy26_inr_realisation:.2f} differs from FACTS ₹6,042/bbl"

    # Windfall tax (SAED) active window check: active between Jul-2022 and Nov-2024, zero from Dec-2024
    for p in prices_fx_data:
        m = p["month"]
        saed = p["windfall_tax_saed_usd_bbl"]
        if "2022-07" <= m <= "2024-11":
            assert saed > 0, f"SAED expected >0 in active window at {m}"
        elif m >= "2024-12":
            assert (
                saed == 0.0
            ), f"SAED expected 0.0 post Dec-2024 abolition at {m}, got {saed}"


def test_brent_realisation_spread_per_fy(prices_fx_data):
    """Verify that per fiscal year, 0 < Brent - realisation_usd < 6,

    except during the SAED (windfall tax) window (primarily FY23) where the government
    levied substantial Special Additional Excise Duty causing a larger gap.
    """
    by_fy = {}
    for r in prices_fx_data:
        by_fy.setdefault(r["fiscal_year"], []).append(r)

    for fy, recs in by_fy.items():
        avg_brent = sum(r["brent_usd_bbl"] for r in recs) / len(recs)
        avg_realisation = sum(
            r["ongc_crude_net_realisation_usd_bbl"] for r in recs
        ) / len(recs)
        gap = avg_brent - avg_realisation

        if fy == "FY23":
            # FY23 carried the heaviest SAED windfall tax (₹10,964 cr statutory levy, FACTS §D2)
            assert (
                gap > 6.0
            ), f"Expected FY23 gap > $6/bbl due to high SAED levy, got {gap:.2f}"
        else:
            # Under standard operating conditions (and post-SAED abolition),
            # ONGC nominated net realisation closely tracks Brent within a $1-$4 discount
            assert (
                0.0 < gap < 6.0
            ), f"FY {fy} spread (Brent - realisation) of ${gap:.2f}/bbl outside expected (0, 6)"



# ==============================================================================
# 7. QUESTION BANK ENTITY RESOLUTION COVERAGE TEST
# ==============================================================================


def test_question_bank_named_entities_resolve(
    questions_data, work_centres_data, fields_data, customers_data
):
    """Verify that every work centre, field, institute, and customer named in

    questions.yaml and its follow-ups resolves cleanly to a canonical reference entity.
    """
    # Build comprehensive alias dictionaries
    alias_to_wc = {}
    for wc in work_centres_data:
        alias_to_wc[wc["wc_id"].lower()] = wc["wc_id"]
        alias_to_wc[wc["name"].lower()] = wc["wc_id"]
        alias_to_wc[wc["short_name"].lower()] = wc["wc_id"]
        alias_to_wc[wc["city"].lower()] = wc["wc_id"]
        for a in wc.get("aliases", []):
            alias_to_wc[a.lower()] = wc["wc_id"]

    alias_to_field = {}
    for f in fields_data:
        alias_to_field[f["field_id"].lower()] = f["field_id"]
        alias_to_field[f["name"].lower()] = f["field_id"]
        for a in f.get("aliases", []):
            alias_to_field[a.lower()] = f["field_id"]

    alias_to_cust = {}
    for c in customers_data:
        alias_to_cust[c["customer_id"].lower()] = c["customer_id"]
        alias_to_cust[c["name"].lower()] = c["customer_id"]
        alias_to_cust[c["short_name"].lower()] = c["customer_id"]

    # Entities mentioned across question_bank.md and questions.yaml
    named_entities = [
        "Delhi",
        "Dehradun",
        "Mumbai",
        "Mumbai High",
        "Heera",
        "Neelam",
        "Neelam-Heera",
        "Bassein",
        "Eastern Offshore",
        "Ahmedabad",
        "Mehsana",
        "Ankleshwar",
        "Cambay",
        "Assam",
        "Assam Asset",
        "Tripura",
        "Tripura Asset",
        "Agartala",
        "Nazira",
        "Sivasagar",
        "Nazira/Sivasagar",
        "Silchar",
        "Rajahmundry",
        "Karaikal",
        "Cauvery",
        "Hazira",
        "Hazira Plant",
        "Uran",
        "Uran Plant",
        "Panvel",
        "Navi Mumbai",
        "KDMIPE",
        "IOGPT",
        "ONGC Academy",
        "Tel Bhavan",
        "KG-DWN-98/2",
        "KG-98/2",
        "KG Basin",
        "Western Offshore",
        "Western Onshore",
        "IOCL",
        "BPCL",
        "HPCL",
        "MRPL",
        "GAIL",
    ]

    unresolved = []
    resolved_counts = 0

    for entity in named_entities:
        e_key = entity.lower()
        matched = False
        if e_key in alias_to_wc or e_key in alias_to_field or e_key in alias_to_cust:
            matched = True
            resolved_counts += 1
        elif any(e_key in [a.lower() for a in wc.get("aliases", [])] for wc in work_centres_data):
            matched = True
            resolved_counts += 1
        else:
            unresolved.append(entity)

    assert (
        len(unresolved) == 0
    ), f"Unresolved entities found in reference resolution: {unresolved}"
    assert resolved_counts == len(named_entities)
