"""Validation test suite for story_register.yaml (Step 1.3).

Verifies:
1. Every story has all required fields with expected types.
2. All entity IDs referenced in stories and personas exist in canonical reference files.
3. Every question of type data, policy_plus_data, what_if, chain, document is served by >=1 story or listed in served_without_story with reason.
4. No two stories contradict on the same metric.
5. Strict numeric sanity and 100% exact equality against calibration_targets.yaml and Lok Sabha LS2067.
6. Formal Assam vacancies strictly equal 30 non-exec / 0 exec matching LS2067.
7. Personas block contains role-only Board members and fictional named E2/E3 officers with complete self-service records.
"""

from pathlib import Path
import re
import pytest
import yaml

DATA_BANK_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = DATA_BANK_ROOT.parent

STORY_REGISTER_PATH = DATA_BANK_ROOT / "world_bible/story_register.yaml"
CALIBRATION_PATH = DATA_BANK_ROOT / "world_bible/calibration_targets.yaml"
QUESTIONS_PATH = DATA_BANK_ROOT / "world_bible/reference/questions.yaml"

REF_DIR = DATA_BANK_ROOT / "world_bible/reference"

REQUIRED_STORY_FIELDS = {
    "id",
    "title",
    "narrative",
    "entities",
    "exact_numbers",
    "who",
    "why",
    "compare",
    "so_what",
    "tables",
    "questions_served",
    "consistency_constraints",
    "test_sql_hint",
}

REQUIRED_ENTITY_KEYS = {
    "work_centres",
    "fields",
    "projects",
    "grades",
    "disciplines",
    "customers",
    "vendors",
    "states",
}

REQUIRED_PERSONA_KEYS = {
    "persona_id",
    "emp_id",
    "name",
    "title",
    "grade",
    "wc_id",
    "discipline",
    "self_service_records",
}

REQUIRED_SELF_SERVICE_KEYS = {
    "leave_balance",
    "transfer_due_date",
    "medical_claim",
    "promotion_eligibility",
    "ta_entitlement",
}


@pytest.fixture(scope="module")
def story_register_data():
    assert STORY_REGISTER_PATH.exists(), f"Missing {STORY_REGISTER_PATH}"
    with open(STORY_REGISTER_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "Root must be a dictionary"
    assert "metadata" in data, "Missing 'metadata'"
    assert "stories" in data, "Missing 'stories'"
    assert "personas" in data, "Missing 'personas'"
    assert "served_without_story" in data, "Missing 'served_without_story'"
    return data


@pytest.fixture(scope="module")
def stories_list(story_register_data):
    return story_register_data["stories"]


@pytest.fixture(scope="module")
def personas_list(story_register_data):
    return story_register_data["personas"]


@pytest.fixture(scope="module")
def questions_data():
    assert QUESTIONS_PATH.exists(), f"Missing {QUESTIONS_PATH}"
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["questions"]


@pytest.fixture(scope="module")
def calibration_data():
    assert CALIBRATION_PATH.exists(), f"Missing {CALIBRATION_PATH}"
    with open(CALIBRATION_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    targets = {t["id"]: t["value"] for t in data["calibration_targets"]}
    return targets


@pytest.fixture(scope="module")
def reference_sets():
    sets = {}
    with open(REF_DIR / "work_centres.yaml", "r", encoding="utf-8") as f:
        sets["work_centres"] = {w["wc_id"] for w in yaml.safe_load(f)["work_centres"]}
    with open(REF_DIR / "fields.yaml", "r", encoding="utf-8") as f:
        sets["fields"] = {w["field_id"] for w in yaml.safe_load(f)["fields"]}
    with open(REF_DIR / "projects.yaml", "r", encoding="utf-8") as f:
        sets["projects"] = {w["prj_id"] for w in yaml.safe_load(f)["projects"]}
    with open(REF_DIR / "grades.yaml", "r", encoding="utf-8") as f:
        sets["grades"] = {w["grade_id"] for w in yaml.safe_load(f)["grades"]}
    with open(REF_DIR / "disciplines.yaml", "r", encoding="utf-8") as f:
        sets["disciplines"] = {w["code"] for w in yaml.safe_load(f)["disciplines"]}
    with open(REF_DIR / "customers.yaml", "r", encoding="utf-8") as f:
        sets["customers"] = {w["customer_id"] for w in yaml.safe_load(f)["customers"]}
    with open(REF_DIR / "vendors.yaml", "r", encoding="utf-8") as f:
        sets["vendors"] = {w["vendor_id"] for w in yaml.safe_load(f)["vendors"]}
    with open(REF_DIR / "geography.yaml", "r", encoding="utf-8") as f:
        sets["states"] = {w["state_code"] for w in yaml.safe_load(f)["states"]}
    return sets


def test_story_count(story_register_data, stories_list):
    """Ensure story register has >= 15 spec stories and >= 35 total stories."""
    assert len(stories_list) >= 35, f"Expected >= 35 stories, found {len(stories_list)}"
    assert story_register_data["metadata"]["total_stories"] == len(stories_list)
    story_ids = [s["id"] for s in stories_list]
    for i in range(1, 16):
        assert f"S{i}" in story_ids, f"Required spec story S{i} missing"


def test_story_fields_and_types(stories_list):
    """Every story must have all required fields with non-empty valid content."""
    for s in stories_list:
        sid = s.get("id")
        missing = REQUIRED_STORY_FIELDS - set(s.keys())
        assert not missing, f"Story {sid} missing fields: {missing}"

        assert isinstance(s["id"], str) and re.match(r"^S\d+$", s["id"])
        assert isinstance(s["title"], str) and len(s["title"]) > 5
        assert isinstance(s["narrative"], str) and len(s["narrative"]) >= 50
        assert isinstance(s["who"], str) and len(s["who"]) > 10
        assert isinstance(s["why"], str) and len(s["why"]) > 10
        assert isinstance(s["compare"], str) and len(s["compare"]) > 10
        assert isinstance(s["so_what"], str) and len(s["so_what"]) > 10
        assert isinstance(s["tables"], list) and len(s["tables"]) >= 1
        assert isinstance(s["questions_served"], list) and len(s["questions_served"]) >= 1
        assert isinstance(s["consistency_constraints"], str) and len(s["consistency_constraints"]) > 10
        assert isinstance(s["test_sql_hint"], str) and "SELECT" in s["test_sql_hint"].upper()

        # Entities check
        assert isinstance(s["entities"], dict)
        missing_ent = REQUIRED_ENTITY_KEYS - set(s["entities"].keys())
        assert not missing_ent, f"Story {sid} missing entity categories: {missing_ent}"
        for ek, ev in s["entities"].items():
            assert isinstance(ev, list), f"Story {sid} entity {ek} must be list"

        # Exact numbers check
        assert isinstance(s["exact_numbers"], dict) and len(s["exact_numbers"]) >= 1
        for num_k, num_v in s["exact_numbers"].items():
            assert "value" in num_v, f"Story {sid} number {num_k} missing 'value'"
            assert "unit" in num_v, f"Story {sid} number {num_k} missing 'unit'"
            assert "computation_definition" in num_v, f"Story {sid} number {num_k} missing 'computation_definition'"


def test_story_and_persona_entities_exist_in_reference(stories_list, personas_list, reference_sets):
    """Every referenced entity ID must exist in reference files."""
    for s in stories_list:
        sid = s["id"]
        for wc in s["entities"]["work_centres"]:
            assert wc in reference_sets["work_centres"], f"Story {sid} invalid wc_id: {wc}"
        for fld in s["entities"]["fields"]:
            assert fld in reference_sets["fields"], f"Story {sid} invalid field_id: {fld}"
        for prj in s["entities"]["projects"]:
            assert prj in reference_sets["projects"], f"Story {sid} invalid prj_id: {prj}"
        for grd in s["entities"]["grades"]:
            assert grd in reference_sets["grades"], f"Story {sid} invalid grade_id: {grd}"
        for disc in s["entities"]["disciplines"]:
            assert disc in reference_sets["disciplines"], f"Story {sid} invalid discipline: {disc}"
        for cust in s["entities"]["customers"]:
            assert cust in reference_sets["customers"], f"Story {sid} invalid customer: {cust}"
        for ven in s["entities"]["vendors"]:
            assert ven in reference_sets["vendors"], f"Story {sid} invalid vendor: {ven}"
        for st in s["entities"]["states"]:
            assert st in reference_sets["states"], f"Story {sid} invalid state: {st}"

    for p in personas_list:
        pid = p["persona_id"]
        assert p["wc_id"] in reference_sets["work_centres"], f"Persona {pid} invalid wc_id: {p['wc_id']}"
        assert p["grade"] in reference_sets["grades"], f"Persona {pid} invalid grade: {p['grade']}"
        assert p["discipline"] in reference_sets["disciplines"], f"Persona {pid} invalid discipline: {p['discipline']}"


def test_all_target_questions_served(questions_data, stories_list, story_register_data):
    """All 89 questions must be accounted for: data/policy_plus_data/what_if/chain/document

    must be served by >=1 story, and policy/refusal questions documented in served_without_story.
    """
    served_by_stories = set()
    for s in stories_list:
        for q_entry in s["questions_served"]:
            base_q = q_entry.split(":")[0].strip()
            served_by_stories.add(base_q)

    served_without_story = {item["question_id"]: item for item in story_register_data["served_without_story"]}

    for q in questions_data:
        qid = q["id"]
        qtype = q["type"]

        if qtype in {"data", "policy_plus_data", "what_if", "chain", "document"}:
            is_served = (qid in served_by_stories) or (qid in served_without_story)
            assert is_served, f"Question {qid} (type: {qtype}) is neither served by a story nor in served_without_story"
        else:
            # policy or refusal
            is_accounted = (qid in served_by_stories) or (qid in served_without_story)
            assert is_accounted, f"Policy/refusal question {qid} is missing from served_without_story"

    # Verify that all 89 questions in total are accounted for
    all_accounted = served_by_stories | set(served_without_story.keys())
    for q in questions_data:
        assert q["id"] in all_accounted, f"Question {q['id']} not accounted for anywhere"


def test_cross_story_invariants(stories_list):
    """No two stories contradict on the same metric or entity facts."""
    stories_map = {s["id"]: s for s in stories_list}

    # S1 Delhi overstay vs S20 AGT transfers out of Delhi
    s1_mandatory_transfers = stories_map["S1"]["exact_numbers"]["delhi_mandatory_transfer_due"]["value"]
    s20_transfers_from_delhi = stories_map["S20"]["exact_numbers"]["transfers_out_of_delhi"]["value"]
    assert s1_mandatory_transfers == s20_transfers_from_delhi == 107

    # S2 NE executive norm shortfall vs S35 Parliament reply norm deficit
    s2_ne_shortfall = stories_map["S2"]["exact_numbers"]["ne_executive_norm_shortfall"]["value"]
    s35_ne_deficit = stories_map["S35"]["exact_numbers"]["ne_executive_manpower_norm_deficit"]["value"]
    assert s2_ne_shortfall == s35_ne_deficit == 191

    # S2 and S35 Assam formal vacancies match LS2067 exactly (30 non-exec, 0 exec)
    assert stories_map["S2"]["exact_numbers"]["assam_formal_sanctioned_vacancies_total"]["value"] == 30
    assert stories_map["S2"]["exact_numbers"]["assam_formal_executive_vacancies"]["value"] == 0
    assert stories_map["S2"]["exact_numbers"]["assam_formal_non_executive_vacancies"]["value"] == 30
    assert stories_map["S35"]["exact_numbers"]["assam_formal_total_vacancies"]["value"] == 30
    assert stories_map["S35"]["exact_numbers"]["assam_formal_executive_vacancies"]["value"] == 0
    assert stories_map["S35"]["exact_numbers"]["assam_formal_group_c_vacancies"]["value"] == 24
    assert stories_map["S35"]["exact_numbers"]["assam_formal_group_d_vacancies"]["value"] == 6

    # S6 Baseline loss fields vs S15 stress baseline
    s6_borholla_ebitda = stories_map["S6"]["exact_numbers"]["borholla_ebitda_inr_cr"]["value"]
    s6_adiyakkamangalam_ebitda = stories_map["S6"]["exact_numbers"]["adiyakkamangalam_ebitda_inr_cr"]["value"]
    assert s6_borholla_ebitda < 0 and s6_adiyakkamangalam_ebitda < 0
    assert stories_map["S15"]["exact_numbers"]["fields_in_loss_at_baseline"]["value"] == 2

    # S9 Projects vs S36 Alerts
    assert "PRJ-0001" in stories_map["S9"]["entities"]["projects"]
    assert "PRJ-0001" in stories_map["S36"]["entities"]["projects"]


def test_numeric_exact_equality_against_calibration(stories_list, calibration_data):
    """Every story number corresponding to a calibration target must match with 100% exact equality."""
    stories_map = {s["id"]: s for s in stories_list}

    # Headcount totals & subsets
    total_hc = calibration_data["CAL-HR-HC-FY26"]
    assert total_hc == 23117
    exec_hc = calibration_data["CAL-HR-STR-EXEC"]
    assert exec_hc == 13781
    nonexec_hc = calibration_data["CAL-HR-STR-NONEXEC"]
    assert nonexec_hc == 9336

    # S16 Affirmative action targets
    assert stories_map["S16"]["exact_numbers"]["total_sc_pct"]["value"] == calibration_data["CAL-HR-DIV-SC-PCT"]
    assert stories_map["S16"]["exact_numbers"]["total_st_pct"]["value"] == calibration_data["CAL-HR-DIV-ST-PCT"]
    assert stories_map["S16"]["exact_numbers"]["total_pwd_headcount"]["value"] == calibration_data["CAL-HR-DIV-PWD-TOT"]

    # S17 Gender diversity targets
    assert stories_map["S17"]["exact_numbers"]["total_female_headcount"]["value"] == calibration_data["CAL-HR-DIV-WOMEN-TOT"]
    assert stories_map["S17"]["exact_numbers"]["total_female_pct"]["value"] == calibration_data["CAL-HR-DIV-WOMEN-PCT"]

    # S21 Statutory levies
    assert stories_map["S21"]["exact_numbers"]["oidb_cess_fy26_cr"]["value"] == calibration_data["CAL-FIN-LEVY-CESS-FY26"]
    assert stories_map["S21"]["exact_numbers"]["royalty_fy26_cr"]["value"] == calibration_data["CAL-FIN-LEVY-ROYALTY-FY26"]
    assert stories_map["S21"]["exact_numbers"]["saed_windfall_fy26_cr"]["value"] == calibration_data["CAL-FIN-LEVY-SAED-FY26"]

    # S23 Receivables
    assert stories_map["S23"]["exact_numbers"]["total_trade_receivables_cr"]["value"] == calibration_data["CAL-FIN-REC-TRADE-FY26"]

    # S28 CSR expenditures
    assert stories_map["S28"]["exact_numbers"]["actual_csr_spend_fy26_cr"]["value"] == calibration_data["CAL-CORP-CSR-TOT-FY26"]
    assert stories_map["S28"]["exact_numbers"]["uttar_pradesh_csr_spend_cr"]["value"] == calibration_data["CAL-CORP-CSR-STATE-UP"]
    assert stories_map["S28"]["exact_numbers"]["maharashtra_csr_spend_cr"]["value"] == calibration_data["CAL-CORP-CSR-STATE-MH"]
    assert stories_map["S28"]["exact_numbers"]["jammu_kashmir_csr_spend_cr"]["value"] == calibration_data["CAL-CORP-CSR-STATE-JK"]

    # S30 Corporate financials & Dividends
    assert stories_map["S30"]["exact_numbers"]["fy26_dividend_per_share_inr"]["value"] == calibration_data["CAL-CORP-DIV-DPS-FY26"]
    assert stories_map["S30"]["exact_numbers"]["fy26_standalone_pat_cr"]["value"] == calibration_data["CAL-FIN-PAT-FY26"]
    assert stories_map["S30"]["exact_numbers"]["fy26_total_dividend_paid_cr"]["value"] == calibration_data["CAL-CORP-DIV-TOT-FY26"]
    assert stories_map["S30"]["exact_numbers"]["fy26_dividend_payout_ratio_pct"]["value"] == calibration_data["CAL-CORP-DIV-PAYOUT-FY26"]
    assert stories_map["S30"]["exact_numbers"]["fy27_budgeted_capex_cr"]["value"] == calibration_data["CAL-FIN-CAPEX-FY26"]

    # S32 Actuarial retirement liabilities
    assert stories_map["S32"]["exact_numbers"]["gratuity_obligation_cr"]["value"] == calibration_data["CAL-FIN-LIAB-GRAT-OBL"]
    assert stories_map["S32"]["exact_numbers"]["gratuity_plan_assets_cr"]["value"] == calibration_data["CAL-FIN-LIAB-GRAT-ASSETS"]
    assert stories_map["S32"]["exact_numbers"]["gratuity_net_liability_cr"]["value"] == calibration_data["CAL-FIN-LIAB-GRAT-NET"]
    assert stories_map["S32"]["exact_numbers"]["prmb_obligation_cr"]["value"] == calibration_data["CAL-FIN-LIAB-PRMB-OBL"]
    assert stories_map["S32"]["exact_numbers"]["prmb_plan_assets_cr"]["value"] == calibration_data["CAL-FIN-LIAB-PRMB-ASSETS"]
    assert stories_map["S32"]["exact_numbers"]["prmb_net_liability_cr"]["value"] == calibration_data["CAL-FIN-LIAB-PRMB-NET"]
    assert stories_map["S32"]["exact_numbers"]["pf_trust_obligation_cr"]["value"] == calibration_data["CAL-FIN-LIAB-PF-OBL"]
    assert stories_map["S32"]["exact_numbers"]["pf_trust_plan_assets_cr"]["value"] == calibration_data["CAL-FIN-LIAB-PF-ASSETS"]
    assert stories_map["S32"]["exact_numbers"]["prbs_pension_defined_contribution_expense_cr"]["value"] == calibration_data["CAL-FIN-LIAB-PRBS-EXP"]
    assert stories_map["S32"]["exact_numbers"]["prbs_contribution_paid_to_trust_cr"]["value"] == calibration_data["CAL-FIN-LIAB-PRBS-CONTRIB"]

    # S33 Subsidiary performance & Group PAT
    assert stories_map["S33"]["exact_numbers"]["group_consolidated_pat_fy26_cr"]["value"] == calibration_data["CAL-CORP-GRP-PAT-FY26"]
    assert stories_map["S33"]["exact_numbers"]["hpcl_standalone_pat_cr"]["value"] == calibration_data["CAL-CORP-SUB-HPCL-PAT"]
    assert stories_map["S33"]["exact_numbers"]["mrpl_standalone_pat_cr"]["value"] == calibration_data["CAL-CORP-SUB-MRPL-PAT"]
    assert stories_map["S33"]["exact_numbers"]["ovl_consolidated_pat_cr"]["value"] == calibration_data["CAL-CORP-SUB-OVL-PAT"]
    assert stories_map["S33"]["exact_numbers"]["opal_ebitda_cr"]["value"] == calibration_data["CAL-CORP-SUB-OPAL-EBITDA"]

    # S34 Energy transition capex & Net Zero roadmap
    assert calibration_data["CAL-CORP-NZ-CAPEX-2030"] == 100000
    assert calibration_data["CAL-CORP-NZ-TARGET-YEAR"] == 2038

    # S35 Parliament reply vacancies for Assam
    assert stories_map["S35"]["exact_numbers"]["assam_formal_total_vacancies"]["value"] == calibration_data["CAL-GOV-PARL-ASSAM-VAC"]


def test_assam_formal_vacancies_match_ls2067(stories_list, calibration_data):
    """Verify that formal vacancies for Assam work centres sum to exactly 30 non-exec / 0 exec."""
    stories_map = {s["id"]: s for s in stories_list}
    s2_nums = stories_map["S2"]["exact_numbers"]
    s35_nums = stories_map["S35"]["exact_numbers"]

    assert s2_nums["assam_formal_sanctioned_vacancies_total"]["value"] == 30
    assert s2_nums["assam_formal_executive_vacancies"]["value"] == 0
    assert s2_nums["assam_formal_non_executive_vacancies"]["value"] == 30

    assert s35_nums["assam_formal_total_vacancies"]["value"] == 30
    assert s35_nums["assam_formal_executive_vacancies"]["value"] == 0
    assert s35_nums["assam_formal_group_c_vacancies"]["value"] == 24
    assert s35_nums["assam_formal_group_d_vacancies"]["value"] == 6
    assert s35_nums["assam_formal_group_c_vacancies"]["value"] + s35_nums["assam_formal_group_d_vacancies"]["value"] == 30


def test_personas_structure_and_role_only_board(personas_list, reference_sets):
    """5 demo personas must exist; Board members (CMD, DIR_HR, DIR_FIN) must be role-only

    without personal names resembling real people, and without personal DOB / retirement dates.
    """
    assert len(personas_list) == 5, f"Expected 5 personas, found {len(personas_list)}"
    persona_map = {p["persona_id"]: p for p in personas_list}
    expected_ids = {"CMD", "DIR_HR", "DIR_FIN", "E2_HR", "E3_FIN"}
    assert set(persona_map.keys()) == expected_ids

    # Board members must be role-only
    board_roles = {"CMD": "Chairman & Chief Executive Officer", "DIR_HR": "Director (Human Resources)", "DIR_FIN": "Director (Finance)"}
    for pid, expected_role_name in board_roles.items():
        p = persona_map[pid]
        assert p["name"] == expected_role_name, f"Persona {pid} name must be role-only '{expected_role_name}', found '{p['name']}'"
        assert "dob" not in p, f"Board persona {pid} must not have personal dob"
        assert "retirement_date" not in p, f"Board persona {pid} must not have personal retirement_date"

    # Fictional named E2/E3 officers
    for pid in ["E2_HR", "E3_FIN"]:
        p = persona_map[pid]
        assert "dob" in p, f"Persona {pid} should have fictional dob"
        assert "retirement_date" in p, f"Persona {pid} should have fictional retirement_date"

    for p in personas_list:
        pid = p["persona_id"]
        missing_keys = REQUIRED_PERSONA_KEYS - set(p.keys())
        assert not missing_keys, f"Persona {pid} missing keys: {missing_keys}"

        assert re.match(r"^EMP-\d{6}$", p["emp_id"]), f"Persona {pid} invalid emp_id format: {p['emp_id']}"
        assert p["grade"] in reference_sets["grades"]
        assert p["wc_id"] in reference_sets["work_centres"]
        assert p["discipline"] in reference_sets["disciplines"]

        # Check self service records
        ssr = p["self_service_records"]
        missing_ssr = REQUIRED_SELF_SERVICE_KEYS - set(ssr.keys())
        assert not missing_ssr, f"Persona {pid} missing self-service records: {missing_ssr}"

        # E1: Leave balance
        assert "earned_leave_days" in ssr["leave_balance"]
        assert "encashable_el_days" in ssr["leave_balance"]
        assert ssr["leave_balance"]["earned_leave_days"] >= ssr["leave_balance"]["encashable_el_days"]

        # E2: Transfer due date
        assert ssr["transfer_due_date"] is not None

        # E3: Medical claim
        assert "claim_id" in ssr["medical_claim"]
        assert "amount_claimed_inr" in ssr["medical_claim"]
        assert "status" in ssr["medical_claim"]

        # E4: Promotion eligibility
        assert "current_grade" in ssr["promotion_eligibility"]
        assert "status" in ssr["promotion_eligibility"]

        # E5: TA entitlement
        assert "travel_class" in ssr["ta_entitlement"]
        assert "lodging_allowance_per_day_inr" in ssr["ta_entitlement"]
        assert "daily_allowance_inr" in ssr["ta_entitlement"]
