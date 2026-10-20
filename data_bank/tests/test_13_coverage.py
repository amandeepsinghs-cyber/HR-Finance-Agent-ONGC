"""Validation test suite for Step 1.4: Question Coverage Map.

Verifies:
1. 89 questions + 267 follow-ups (356 entries total) are all present in question_coverage.yaml.
2. Every table and column referenced in tables/columns exists in schema_silver.yaml.
3. Every document reference exists in policy_question_map.yaml (registry or reconstruction_requirements).
4. Every story ID referenced in story_ids exists in story_register.yaml (S1..S38).
5. answerable=True and gap=None for all entries, and top-level gaps list is empty.
6. Every gold_layer_object referenced is defined in gold_marts summary section, with valid source silver tables and bidirectional tracking.
7. All answer_type and expected_output values conform to canonical vocabulary.
"""

from pathlib import Path
import pytest
import yaml

DATA_BANK_ROOT = Path(__file__).resolve().parent.parent
WORLD_BIBLE_DIR = DATA_BANK_ROOT / "world_bible"

COVERAGE_YAML_PATH = WORLD_BIBLE_DIR / "question_coverage.yaml"
QUESTIONS_YAML_PATH = WORLD_BIBLE_DIR / "reference" / "questions.yaml"
SCHEMA_SILVER_PATH = WORLD_BIBLE_DIR / "schema_silver.yaml"
POLICY_MAP_PATH = WORLD_BIBLE_DIR / "policy_question_map.yaml"
STORY_REGISTER_PATH = WORLD_BIBLE_DIR / "story_register.yaml"

VALID_ANSWER_TYPES = {
    "sql",
    "rag",
    "sql_plus_rag",
    "what_if_sim",
    "document_gen",
    "refusal",
}

VALID_OUTPUTS = {
    "number",
    "table",
    "list",
    "chart",
    "document",
    "refusal",
}

VALID_PERSONAS = {
    "CMD",
    "Director (HR)",
    "Director (Finance)",
    "E1–E4 Officer (HR)",
    "E1–E4 Officer (Finance)",
}

EXPECTED_KINDS = {"drill_down", "why", "compare_or_so_what"}


@pytest.fixture(scope="module")
def coverage_data():
    assert COVERAGE_YAML_PATH.exists(), f"Missing {COVERAGE_YAML_PATH}"
    with open(COVERAGE_YAML_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "question_coverage.yaml root must be a dict"
    assert "entries" in data, "question_coverage.yaml must contain 'entries' key"
    assert "gold_marts" in data, "question_coverage.yaml must contain 'gold_marts' key"
    assert "gaps" in data, "question_coverage.yaml must contain 'gaps' key"
    return data


@pytest.fixture(scope="module")
def questions_data():
    assert QUESTIONS_YAML_PATH.exists(), f"Missing {QUESTIONS_YAML_PATH}"
    with open(QUESTIONS_YAML_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["questions"]


@pytest.fixture(scope="module")
def silver_schema_data():
    assert SCHEMA_SILVER_PATH.exists(), f"Missing {SCHEMA_SILVER_PATH}"
    with open(SCHEMA_SILVER_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


@pytest.fixture(scope="module")
def policy_map_data():
    assert POLICY_MAP_PATH.exists(), f"Missing {POLICY_MAP_PATH}"
    with open(POLICY_MAP_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


@pytest.fixture(scope="module")
def story_register_data():
    assert STORY_REGISTER_PATH.exists(), f"Missing {STORY_REGISTER_PATH}"
    with open(STORY_REGISTER_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


def test_coverage_file_exists_and_metadata(coverage_data):
    metadata = coverage_data.get("metadata", {})
    assert metadata.get("total_questions") == 89, "Metadata total_questions must be 89"
    assert metadata.get("total_followups") == 267, "Metadata total_followups must be 267"
    assert metadata.get("total_entries") == 356, "Metadata total_entries must be 356"


def test_89_questions_and_267_followups_all_present(coverage_data, questions_data):
    entries = coverage_data["entries"]
    assert len(entries) == 356, f"Expected exactly 356 entries, found {len(entries)}"

    entry_map = {e["id"]: e for e in entries}
    assert len(entry_map) == 356, "Duplicate IDs detected in question_coverage.yaml"

    root_entries = [e for e in entries if e.get("parent_id") is None]
    assert len(root_entries) == 89, f"Expected 89 root questions, found {len(root_entries)}"

    followup_entries = [e for e in entries if e.get("parent_id") is not None]
    assert len(followup_entries) == 267, f"Expected 267 follow-ups, found {len(followup_entries)}"

    # Validate against reference questions.yaml
    for q in questions_data:
        qid = q["id"]
        assert qid in entry_map, f"Root question ID '{qid}' missing from coverage map"
        root_e = entry_map[qid]
        assert root_e["text"] == q["question"], f"Text mismatch for root question '{qid}'"
        assert root_e["parent_id"] is None, f"parent_id for root '{qid}' must be None"

        # Check all 3 follow-ups
        assert len(q["followups"]) == 3, f"Question '{qid}' must have exactly 3 followups"
        for fu in q["followups"]:
            kind = fu["kind"]
            fu_id = f"{qid}.{kind}"
            assert fu_id in entry_map, f"Follow-up ID '{fu_id}' missing from coverage map"
            fu_e = entry_map[fu_id]
            assert fu_e["parent_id"] == qid, f"parent_id for '{fu_id}' must be '{qid}'"
            assert fu_e["text"] == fu["question"], f"Text mismatch for follow-up '{fu_id}'"


def test_every_table_and_column_exists_in_schema_silver(coverage_data, silver_schema_data):
    valid_tables = {
        t["table_name"]: {c["name"] for c in t.get("columns", [])}
        for t in silver_schema_data.get("tables", [])
    }
    assert len(valid_tables) == 53, f"Expected 53 tables in schema_silver.yaml, got {len(valid_tables)}"

    errors = []
    for e in coverage_data["entries"]:
        eid = e["id"]
        tables = e.get("tables", [])
        columns = e.get("columns", [])

        # Check declared tables
        for t in tables:
            if t not in valid_tables:
                errors.append(f"Entry '{eid}': table '{t}' does not exist in schema_silver.yaml")

        # Check declared columns
        for col in columns:
            if "." not in col:
                errors.append(f"Entry '{eid}': column '{col}' is not formatted as 'table.column'")
                continue
            tbl, cname = col.split(".", 1)
            if tbl not in valid_tables:
                errors.append(f"Entry '{eid}': column '{col}' references non-existent table '{tbl}'")
            elif cname not in valid_tables[tbl]:
                errors.append(f"Entry '{eid}': column '{cname}' does not exist in silver table '{tbl}'")

    assert not errors, f"Schema validation failures ({len(errors)}):\n" + "\n".join(errors[:25])


def test_every_doc_reference_exists_in_policy_map(coverage_data, policy_map_data):
    valid_doc_ids = {d["doc_id"] for d in policy_map_data.get("documents", [])}
    reconstruction_keys = set(policy_map_data.get("reconstruction_requirements", {}).keys())

    errors = []
    for e in coverage_data["entries"]:
        eid = e["id"]
        docs = e.get("documents", [])
        for doc in docs:
            # Must match doc_id, reconstruction rulebook, or prefix
            matched = False
            if doc in valid_doc_ids or doc in reconstruction_keys:
                matched = True
            else:
                for k in reconstruction_keys:
                    if doc.startswith(k):
                        matched = True
                        break
                if not matched:
                    for d in valid_doc_ids:
                        if doc.startswith(d):
                            matched = True
                            break
            if not matched:
                errors.append(f"Entry '{eid}': document '{doc}' not found in policy registry or reconstruction targets")

    assert not errors, f"Document reference failures ({len(errors)}):\n" + "\n".join(errors[:25])


def test_every_story_id_exists(coverage_data, story_register_data):
    valid_story_ids = {s["id"] for s in story_register_data.get("stories", [])}
    assert len(valid_story_ids) == 38, f"Expected 38 stories in story_register.yaml, got {len(valid_story_ids)}"

    errors = []
    for e in coverage_data["entries"]:
        eid = e["id"]
        story_ids = e.get("story_ids", [])
        for sid in story_ids:
            if sid not in valid_story_ids:
                errors.append(f"Entry '{eid}': story ID '{sid}' does not exist in story_register.yaml")

    assert not errors, f"Story ID failures ({len(errors)}):\n" + "\n".join(errors[:25])


def test_answerable_true_for_all_and_no_gaps(coverage_data):
    entries = coverage_data["entries"]
    unanswerable = [e["id"] for e in entries if e.get("answerable") is not True]
    assert not unanswerable, f"Entries marked answerable=False: {unanswerable}"

    gaps_with_reasons = [e["id"] for e in entries if e.get("gap") is not None]
    assert not gaps_with_reasons, f"Entries with gaps reported: {gaps_with_reasons}"

    top_level_gaps = coverage_data.get("gaps", [])
    assert len(top_level_gaps) == 0, f"Top-level gaps section is not empty: {top_level_gaps}"


def test_every_gold_mart_referenced_is_defined_in_gold_marts(coverage_data, silver_schema_data):
    gold_marts = coverage_data.get("gold_marts", {})
    if isinstance(gold_marts, dict):
        defined_marts = set(gold_marts.keys())
    else:
        defined_marts = {m["name"] for m in gold_marts}

    assert 10 <= len(defined_marts) <= 16, f"Expected 10-16 gold marts, found {len(defined_marts)}"

    valid_silver_tables = {t["table_name"] for t in silver_schema_data.get("tables", [])}

    # Verify each gold mart definition
    if isinstance(gold_marts, dict):
        marts_iter = gold_marts.values()
    else:
        marts_iter = gold_marts

    for mart in marts_iter:
        m_name = mart.get("name")
        assert m_name, "Gold mart missing 'name'"
        assert mart.get("description"), f"Gold mart '{m_name}' missing description"
        src_tables = mart.get("source_silver_tables", [])
        for st in src_tables:
            assert st in valid_silver_tables, f"Gold mart '{m_name}' references non-existent silver table '{st}'"
        serves = mart.get("serves_entries", [])
        assert isinstance(serves, list), f"Gold mart '{m_name}' serves_entries must be a list"
        assert len(serves) > 0, f"Gold mart '{m_name}' has empty serves_entries"

    # Verify that every entry's gold_layer_object is in defined_marts
    errors = []
    for e in coverage_data["entries"]:
        eid = e["id"]
        gm = e.get("gold_layer_object")
        if not gm:
            errors.append(f"Entry '{eid}' missing gold_layer_object")
        elif gm not in defined_marts:
            errors.append(f"Entry '{eid}' references undefined gold mart '{gm}'")

    assert not errors, f"Gold mart reference failures ({len(errors)}):\n" + "\n".join(errors[:25])


def test_canonical_answer_types_and_expected_outputs(coverage_data):
    for e in coverage_data["entries"]:
        eid = e["id"]
        atype = e.get("answer_type")
        assert atype in VALID_ANSWER_TYPES, f"Entry '{eid}' has invalid answer_type '{atype}'"

        out = e.get("expected_output")
        assert out in VALID_OUTPUTS, f"Entry '{eid}' has invalid expected_output '{out}'"

        personas = e.get("personas", [])
        assert isinstance(personas, list) and len(personas) >= 1, f"Entry '{eid}' has invalid personas list"
        for p in personas:
            assert p in VALID_PERSONAS, f"Entry '{eid}' has invalid persona '{p}'"
