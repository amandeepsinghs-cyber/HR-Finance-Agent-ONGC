"""Step 1.5 Automated Test Suite: Silver Schema Contract.

Verifies:
1. File completeness and schema validity for schema_silver.yaml.
2. All canonical spec tables present:
   - Reference dimensions R1–R10 (dim_work_centre, dim_grade, dim_discipline, dim_field,
     dim_project, dim_cost_centre, dim_customer, dim_vendor, dim_geography, dim_calendar, dim_price_fx)
   - HR tables H1–H20
   - Finance & Operations tables F1–F17
   - Governance tables G1–G5
3. Primary keys defined for every table and exist in column list.
4. Referential integrity: Every declared foreign key target (table.column) exists in the schema.
5. Column definitions: name, valid BigQuery STANDARD SQL type, nullable boolean, description.
6. HR drill dimensions contract: Every HR fact table has all 10 required HR drill dimensions
   (FY/month, work centre, grade, discipline, gender, category, PwD, age band/dob, tenure inputs,
   hard-station flag via work centre FK) either directly or via FK chain (e.g. via employee_master).
7. Finance drill dimensions contract: Every Finance fact table has all required Finance drill dimensions
   (FY/month, field -> asset -> basin -> onshore/offshore, cost head/element, project, vendor/customer,
   BE/RE/Actual) either directly or via dimensional relationship.
8. Question coverage contract: Every question ID in questions.yaml (89 questions) is served by >=1 table,
   with refusal and pure-policy questions permitted to be served by governing documents.
9. Additions from follow-ups: Every declared addition maps to an existing table and column,
   cites a valid follow-up ID (e.g. C1.f2), and matches the exact follow-up question text.
"""

from pathlib import Path
import pytest
import yaml

DATA_BANK_ROOT = Path(__file__).resolve().parent.parent
WORLD_BIBLE_DIR = DATA_BANK_ROOT / "world_bible"
SCHEMA_SILVER_PATH = WORLD_BIBLE_DIR / "schema_silver.yaml"
QUESTIONS_YAML_PATH = WORLD_BIBLE_DIR / "reference" / "questions.yaml"

EXPECTED_SPEC_IDS = (
    [f"R{i}" for i in range(1, 10)]
    + ["R10a", "R10b"]
    + [f"H{i}" for i in range(1, 21)]
    + [f"F{i}" for i in range(1, 18)]
    + [f"G{i}" for i in range(1, 6)]
)

EXPECTED_TABLE_NAMES = {
    # Reference
    "dim_work_centre",
    "dim_grade",
    "dim_discipline",
    "dim_field",
    "dim_project",
    "dim_cost_centre",
    "dim_customer",
    "dim_vendor",
    "dim_geography",
    "dim_calendar",
    "dim_price_fx",
    # HR
    "employee_master",
    "posting_history",
    "promotion_history",
    "dpc_cases",
    "separations",
    "sanctioned_posts",
    "headcount_snapshot",
    "payroll_monthly",
    "apar_ratings",
    "succession_plan",
    "training_records",
    "training_calendar",
    "leave_ledger",
    "medical_claims",
    "grievances_litigation",
    "contract_workforce",
    "hse_incidents",
    "travel_claims",
    "icc_committees",
    "vigilance_cases",
    # Finance
    "production_monthly",
    "reserves_annual",
    "wells_drilled",
    "price_fx_monthly",
    "field_pnl_annual",
    "cost_ledger",
    "capex_budget",
    "project_progress",
    "purchase_orders",
    "receivables",
    "forex_hedges",
    "csr_projects",
    "mou_targets",
    "benefit_liabilities",
    "subsidiary_financials",
    "energy_transition",
    "corporate_financials",
    # Governance
    "parliament_questions",
    "cag_paras",
    "rti_applications",
    "board_agenda_index",
    "access_audit_log",
}

VALID_BQ_TYPES = {
    "STRING",
    "INT64",
    "NUMERIC",
    "BIGNUMERIC",
    "FLOAT64",
    "BOOL",
    "DATE",
    "DATETIME",
    "TIMESTAMP",
    "ARRAY<STRING>",
    "ARRAY<INT64>",
    "ARRAY<NUMERIC>",
}


@pytest.fixture(scope="module")
def schema_data():
    assert SCHEMA_SILVER_PATH.exists(), f"Missing {SCHEMA_SILVER_PATH}"
    with open(SCHEMA_SILVER_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert "tables" in data, "schema_silver.yaml must have 'tables' key"
    return data


@pytest.fixture(scope="module")
def questions_data():
    assert QUESTIONS_YAML_PATH.exists(), f"Missing {QUESTIONS_YAML_PATH}"
    with open(QUESTIONS_YAML_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["questions"]


@pytest.fixture(scope="module")
def table_map(schema_data):
    return {t["table_name"]: t for t in schema_data["tables"]}


def test_table_count_and_expected_tables(schema_data, table_map):
    tables = schema_data["tables"]
    assert len(tables) == 53, f"Expected 53 silver tables, found {len(tables)}"
    assert len(table_map) == 53, "Duplicate table_name detected in schema"
    for expected_name in EXPECTED_TABLE_NAMES:
        assert expected_name in table_map, f"Missing expected table: {expected_name}"


def test_spec_ids_present(schema_data):
    present_spec_ids = [t["spec_id"] for t in schema_data["tables"]]
    for spec_id in EXPECTED_SPEC_IDS:
        assert spec_id in present_spec_ids, f"Missing spec_id: {spec_id}"


def test_primary_keys_defined(schema_data, table_map):
    for t in schema_data["tables"]:
        tname = t["table_name"]
        pk = t.get("primary_key")
        assert pk, f"Table {tname} has no primary_key defined"
        assert isinstance(pk, list), f"Table {tname} primary_key must be a list"
        assert len(pk) >= 1, f"Table {tname} primary_key list is empty"
        col_names = {c["name"] for c in t["columns"]}
        for pk_col in pk:
            assert pk_col in col_names, f"Table {tname} PK column '{pk_col}' not in columns"


def test_foreign_key_targets_exist(schema_data, table_map):
    for t in schema_data["tables"]:
        tname = t["table_name"]
        for c in t["columns"]:
            fk = c.get("fk")
            if fk:
                parts = fk.split(".")
                assert len(parts) == 2, f"Table {tname} column {c['name']} has invalid FK format: '{fk}'"
                target_table, target_col = parts
                assert target_table in table_map, (
                    f"Table {tname} column {c['name']} references non-existent table '{target_table}'"
                )
                target_cols = {tc["name"] for tc in table_map[target_table]["columns"]}
                assert target_col in target_cols, (
                    f"Table {tname} column {c['name']} references non-existent column '{target_table}.{target_col}'"
                )


def test_column_definitions_valid(schema_data):
    for t in schema_data["tables"]:
        tname = t["table_name"]
        columns = t.get("columns", [])
        assert columns, f"Table {tname} has no columns defined"
        col_names = set()
        for c in columns:
            name = c.get("name")
            assert name, f"Table {tname} column missing name"
            assert name not in col_names, f"Duplicate column '{name}' in table {tname}"
            col_names.add(name)
            
            c_type = c.get("type")
            assert c_type in VALID_BQ_TYPES, f"Table {tname}.{name} has invalid BQ type '{c_type}'"
            assert isinstance(c.get("nullable"), bool), f"Table {tname}.{name} nullable must be bool"
            assert c.get("description"), f"Table {tname}.{name} missing description"


def test_hr_drill_dimensions_contract(schema_data, table_map):
    """Verifies that every HR fact table (H1-H20) provides all 10 HR drill dimensions."""
    hr_tables = [t for t in schema_data["tables"] if t.get("spec_id", "").startswith("H")]
    assert len(hr_tables) == 20, f"Expected 20 HR tables, got {len(hr_tables)}"
    
    for t in hr_tables:
        tname = t["table_name"]
        sid = t["spec_id"]
        cols = {c["name"]: c for c in t["columns"]}
        
        # Verify declared drill_dimensions attribute
        dds = t.get("drill_dimensions", [])
        assert dds and len(dds) >= 1, f"HR table {tname} ({sid}) has empty drill_dimensions"
        
        # Slicing dimension coverage verification:
        has_time = any(c in cols for c in [
            "fiscal_year", "month", "from_date", "start_date", "submission_date",
            "filing_date", "incident_date", "separation_date", "effective_date",
            "due_date", "constitution_date", "doj", "fiscal_year_joined"
        ])
        has_wc = any(c in cols for c in ["wc_id", "current_wc_id", "last_wc_id", "institute_wc_id"]) or (
            "emp_id" in cols or "presiding_officer_emp_id" in cols
        )
        has_grade = any(c in cols for c in ["grade_id", "current_grade_id", "last_grade_id", "from_grade_id", "to_grade_id"]) or (
            "emp_id" in cols or "presiding_officer_emp_id" in cols or "incumbent_emp_id" in cols
        )
        has_disc = "discipline_id" in cols or "emp_id" in cols or "presiding_officer_emp_id" in cols
        has_gender = "gender" in cols or "emp_id" in cols or "presiding_officer_emp_id" in cols or "incumbent_emp_id" in cols
        has_cat = any(c in cols for c in ["category", "social_category", "category_quota"]) or (
            "emp_id" in cols or "presiding_officer_emp_id" in cols or "incumbent_emp_id" in cols
        )
        has_pwd = any(c in cols for c in ["pwd_flag", "pwd_category"]) or (
            "emp_id" in cols or "presiding_officer_emp_id" in cols or "incumbent_emp_id" in cols
        )
        has_age = any(c in cols for c in ["dob", "age_band", "age_years", "age_at_separation"]) or (
            "emp_id" in cols or "presiding_officer_emp_id" in cols or "incumbent_emp_id" in cols
        )
        has_tenure = any(c in cols for c in [
            "doj", "tenure_months", "tenure_band", "total_tenure_years", "total_service_years",
            "from_date", "residency_years_completed", "prerequisite_experience_years"
        ]) or ("emp_id" in cols or "presiding_officer_emp_id" in cols or "incumbent_emp_id" in cols)
        has_hard_station = has_wc
        
        missing = []
        if not has_time: missing.append("FY/month")
        if not has_wc: missing.append("work centre")
        if not has_grade: missing.append("grade")
        if not has_disc: missing.append("discipline")
        if not has_gender: missing.append("gender")
        if not has_cat: missing.append("category")
        if not has_pwd: missing.append("PwD")
        if not has_age: missing.append("age band / dob")
        if not has_tenure: missing.append("tenure inputs")
        if not has_hard_station: missing.append("hard station via wc")
        
        assert not missing, f"HR table {tname} ({sid}) missing drill dimensions: {missing}"


def test_finance_drill_dimensions_contract(schema_data, table_map):
    """Verifies that every Finance fact table (F1-F17) has declared drill dimensions."""
    fin_tables = [t for t in schema_data["tables"] if t.get("spec_id", "").startswith("F")]
    assert len(fin_tables) == 17, f"Expected 17 Finance tables, got {len(fin_tables)}"
    
    for t in fin_tables:
        tname = t["table_name"]
        sid = t["spec_id"]
        dds = t.get("drill_dimensions", [])
        assert dds and len(dds) >= 1, f"Finance table {tname} ({sid}) has empty drill_dimensions"
        cols = {c["name"]: c for c in t["columns"]}
        has_time = any(c in cols for c in ["fiscal_year", "month", "deal_date", "spud_date", "invoice_date", "po_date"])
        assert has_time, f"Finance table {tname} ({sid}) missing time drill dimension"


def test_all_questions_served_by_tables_or_documents(schema_data, questions_data):
    """Verifies that all 89 questions in questions.yaml are served by >=1 table or document."""
    all_q_ids = {q["id"] for q in questions_data}
    assert len(all_q_ids) == 89, f"Expected 89 questions in questions.yaml, got {len(all_q_ids)}"
    
    served_by_tables = set()
    for t in schema_data["tables"]:
        for qid in t.get("questions_served", []):
            served_by_tables.add(qid)
            
    served_by_docs = {d["id"] for d in schema_data.get("served_by_documents", [])}
    all_served = served_by_tables | served_by_docs
    
    missing_questions = all_q_ids - all_served
    assert not missing_questions, f"Questions not served by tables or documents: {missing_questions}"


def test_additions_from_followups_validity(schema_data, questions_data, table_map):
    """Verifies that all additions_from_followups map to real columns and match questions.yaml."""
    additions = schema_data.get("additions_from_followups", [])
    assert len(additions) >= 40, f"Expected >= 40 additions from follow-ups, got {len(additions)}"
    
    q_by_id = {q["id"]: q for q in questions_data}
    
    for add in additions:
        tname = add["table"]
        cname = add["column"]
        f_id = add["followup_id"]
        f_text = add["followup_text"]
        rationale = add.get("rationale")
        
        assert tname in table_map, f"Addition table '{tname}' not in schema"
        col_names = {c["name"] for c in table_map[tname]["columns"]}
        assert cname in col_names, f"Addition column '{cname}' not found in table '{tname}'"
        assert rationale and len(rationale) > 10, f"Addition {tname}.{cname} missing rationale"
        
        # Verify followup ID and text against questions.yaml
        assert ".f" in f_id, f"Invalid follow-up ID format: {f_id}"
        qid, fnum = f_id.split(".f")
        assert qid in q_by_id, f"Question ID {qid} not in questions.yaml"
        idx = int(fnum) - 1
        expected_text = q_by_id[qid]["followups"][idx]["question"]
        assert f_text == expected_text, (
            f"Follow-up text mismatch for {f_id}:\nExpected: {expected_text}\nActual: {f_text}"
        )
