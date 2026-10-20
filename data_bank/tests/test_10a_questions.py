"""Validation test suite for questions.yaml (Step 1.0)."""

import re
from pathlib import Path
import pytest
import yaml

DATA_BANK_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = DATA_BANK_ROOT.parent
BANK_PATH = PROJECT_ROOT / "docs/question_bank.md"
QUESTIONS_YAML_PATH = DATA_BANK_ROOT / "world_bible/reference/questions.yaml"

EXPECTED_IDS = (
    [f"C{i}" for i in range(1, 15)]
    + [f"H{i}" for i in range(1, 11)]
    + [f"F{i}" for i in range(1, 11)]
    + [f"E{i}" for i in range(1, 8)]
    + [f"D{i}" for i in range(1, 7)]
    + [f"P{i}" for i in range(1, 21)]
    + [f"T{i}" for i in range(1, 4)]
    + [f"W{i}" for i in range(1, 5)]
    + [f"M{i}" for i in range(1, 6)]
    + [f"X{i}" for i in range(1, 11)]
)

VALID_TYPES = {
    "data",
    "policy",
    "policy_plus_data",
    "refusal",
    "chain",
    "what_if",
    "document",
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
def questions_data():
    assert QUESTIONS_YAML_PATH.exists(), f"Missing {QUESTIONS_YAML_PATH}"
    with open(QUESTIONS_YAML_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert "questions" in data, "YAML root must have 'questions' key"
    return data["questions"]


@pytest.fixture(scope="module")
def bank_text_map():
    assert BANK_PATH.exists(), f"Missing {BANK_PATH}"
    content = BANK_PATH.read_text(encoding="utf-8")
    mapping = {}
    for line in content.splitlines():
        line = line.strip()
        if (
            not line.startswith("|")
            or line.startswith("| #")
            or line.startswith("|---")
            or line.startswith("| Chain")
            or line.startswith("| Question")
        ):
            continue
        cols = [c.strip() for c in line.split("|")[1:-1]]
        if not cols:
            continue
        id_m = re.match(
            r"^(C\d+|H\d+|F\d+|E\d+|D\d+|P\d+|T\d+|W\d+|M\d+|X\d+)", cols[0]
        )
        if id_m:
            qid = id_m.group(1)
            if qid.startswith("T"):
                mapping[qid] = cols[1]
            elif qid.startswith("X"):
                mapping[qid] = cols[2]
            else:
                mapping[qid] = cols[1]
    return mapping


def test_all_expected_ids_present(questions_data):
    ids = [q["id"] for q in questions_data]
    assert len(ids) == len(
        EXPECTED_IDS
    ), f"Expected {len(EXPECTED_IDS)} questions, got {len(ids)}"
    for expected_id in EXPECTED_IDS:
        assert expected_id in ids, f"Expected ID {expected_id} not found"


def test_no_duplicate_ids(questions_data):
    ids = [q["id"] for q in questions_data]
    assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"


def test_required_fields_non_empty(questions_data):
    for q in questions_data:
        qid = q.get("id")
        assert qid, "Empty or missing id"
        assert q.get("group"), f"Empty or missing group in {qid}"
        assert q.get("personas"), f"Empty or missing personas in {qid}"
        assert isinstance(q["personas"], list), f"personas must be a list in {qid}"
        for p in q["personas"]:
            assert p in VALID_PERSONAS, f"Invalid persona '{p}' in {qid}"
        assert q.get("question"), f"Empty or missing question in {qid}"
        assert q.get("decision_it_drives"), f"Empty or missing decision_it_drives in {qid}"
        assert q.get("type") in VALID_TYPES, f"Invalid type '{q.get('type')}' in {qid}"
        assert (
            q.get("expected_output") in VALID_OUTPUTS
        ), f"Invalid expected_output '{q.get('expected_output')}' in {qid}"


def test_chain_steps_present_and_valid(questions_data):
    chains = [q for q in questions_data if q["id"].startswith("T")]
    assert len(chains) == 3, f"Expected 3 chains, got {len(chains)}"
    for chain in chains:
        assert "steps" in chain, f"Chain {chain['id']} missing 'steps' field"
        assert isinstance(chain["steps"], list), f"Chain {chain['id']} 'steps' must be a list"
        assert len(chain["steps"]) >= 3, f"Chain {chain['id']} must have >= 3 steps"
        for step in chain["steps"]:
            assert isinstance(step, str) and len(step) > 0


def test_three_followups_each_with_three_kinds(questions_data):
    for q in questions_data:
        qid = q.get("id")
        followups = q.get("followups")
        assert isinstance(followups, list), f"followups in {qid} must be a list"
        assert len(followups) == 3, f"{qid} must have exactly 3 followups, got {len(followups)}"
        
        kinds = set()
        for fu in followups:
            kind = fu.get("kind")
            question = fu.get("question")
            assert kind in EXPECTED_KINDS, f"Invalid kind '{kind}' in {qid}"
            assert question and len(question.strip()) > 10, f"Followup question too short in {qid}"
            kinds.add(kind)
            
        assert kinds == EXPECTED_KINDS, f"{qid} missing some expected kinds: {kinds} vs {EXPECTED_KINDS}"


def test_question_text_matches_bank(questions_data, bank_text_map):
    for q in questions_data:
        qid = q["id"]
        assert qid in bank_text_map, f"ID {qid} not found in question bank markdown"
        bank_q = bank_text_map[qid]
        assert (
            q["question"] == bank_q
        ), f"Question text mismatch for {qid}:\nYAML: {q['question']}\nBANK: {bank_q}"
