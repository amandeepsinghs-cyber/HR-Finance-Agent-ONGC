"""Validation test suite for Step 1.6: Real policy registry & question map.

Checks:
1. Every policy-type question (types policy and policy_plus_data in questions.yaml) is mapped.
2. Every mapped doc_id exists in registry and its text file exists on disk.
3. Every answered_by_real quote is actually found in the text file (normalised whitespace, case-insensitive substring) and <= 60 words.
4. Every needs_reconstruction item appears in reconstruction_requirements.
5. All 7 target rulebooks for Step 3.1 demo reconstructions are fully specified with clauses and real excerpts.
"""

import re
from pathlib import Path
import pytest
import yaml

DATA_BANK_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = DATA_BANK_ROOT.parent
POLICY_MAP_PATH = DATA_BANK_ROOT / "world_bible/policy_question_map.yaml"
QUESTIONS_YAML_PATH = DATA_BANK_ROOT / "world_bible/reference/questions.yaml"

REQUIRED_RULEBOOKS = {
    "JRTP",
    "BDP summary",
    "Leave Rules",
    "R&P/Promotion",
    "HR Manual",
    "PRBS",
    "Post-retirement medical",
}

VALID_STATUSES = {
    "answered_by_real",
    "partial_real",
    "needs_reconstruction",
}

VALID_FIDELITIES = {
    "full",
    "excerpt",
    "reference",
}


def normalize(text: str) -> str:
    """Normalize quotes, dashes, whitespace, and case for fuzzy substring matching."""
    s = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


@pytest.fixture(scope="module")
def policy_data():
    """Load policy_question_map.yaml once for the test module."""
    assert POLICY_MAP_PATH.exists(), f"File missing: {POLICY_MAP_PATH}"
    with open(POLICY_MAP_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "policy_question_map.yaml root must be a dict"
    return data


@pytest.fixture(scope="module")
def questions_data():
    """Load questions.yaml once for the test module."""
    assert QUESTIONS_YAML_PATH.exists(), f"File missing: {QUESTIONS_YAML_PATH}"
    with open(QUESTIONS_YAML_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("questions", [])


def test_documents_registry_schema_and_files(policy_data):
    """Test that documents registry contains 78 collected real documents and each text file exists."""
    docs = policy_data.get("documents", [])
    assert len(docs) == 78, f"Expected 78 documents in registry, found {len(docs)}"

    seen_ids = set()
    for doc in docs:
        doc_id = doc.get("doc_id")
        assert doc_id, f"Missing doc_id in doc: {doc}"
        assert doc_id not in seen_ids, f"Duplicate doc_id: {doc_id}"
        seen_ids.add(doc_id)

        assert doc.get("title"), f"Missing title in {doc_id}"
        assert doc.get("issuer"), f"Missing issuer in {doc_id}"
        assert doc.get("year"), f"Missing year in {doc_id}"
        assert doc.get("source_type"), f"Missing source_type in {doc_id}"
        assert doc.get("confidentiality") == "public", f"Confidentiality must be public in {doc_id}"
        assert doc.get("fidelity") in VALID_FIDELITIES, f"Invalid fidelity in {doc_id}: {doc.get('fidelity')}"

        text_path_str = doc.get("text_path")
        assert text_path_str, f"Missing text_path in {doc_id}"
        abs_text_path = PROJECT_ROOT / text_path_str
        assert abs_text_path.exists(), f"Text file missing on disk for {doc_id}: {abs_text_path}"
        assert abs_text_path.stat().st_size > 0, f"Text file empty for {doc_id}: {abs_text_path}"


def test_every_policy_question_is_mapped(policy_data, questions_data):
    """Test that every question of type 'policy' and 'policy_plus_data' in questions.yaml is mapped."""
    qmap = policy_data.get("question_map", [])
    mapped_ids = {item["id"] for item in qmap}

    policy_type_questions = [
        q["id"] for q in questions_data if q.get("type") in ("policy", "policy_plus_data")
    ]
    assert len(policy_type_questions) == 20, f"Expected 20 policy-type questions, found {len(policy_type_questions)}"

    for qid in policy_type_questions:
        assert qid in mapped_ids, f"Policy question {qid} is missing from question_map in policy_question_map.yaml!"


def test_mapped_doc_ids_exist_in_registry_and_disk(policy_data):
    """Test that every doc_id cited in question_map exists in documents registry and its text file exists."""
    docs = policy_data.get("documents", [])
    doc_registry = {d["doc_id"]: d for d in docs}
    qmap = policy_data.get("question_map", [])

    for item in qmap:
        qid = item.get("id")
        doc_ids = item.get("doc_ids", [])
        assert doc_ids, f"No doc_ids specified for mapped item {qid}"
        for did in doc_ids:
            assert did in doc_registry, f"Mapped doc_id '{did}' in {qid} does not exist in documents registry!"
            text_path = PROJECT_ROOT / doc_registry[did]["text_path"]
            assert text_path.exists(), f"Text file for doc_id '{did}' missing: {text_path}"


def test_answered_by_real_quotes_found_in_text(policy_data):
    """Test that every answered_by_real item has a valid verbatim quote (<=60 words) found in text."""
    docs = policy_data.get("documents", [])
    doc_registry = {d["doc_id"]: d for d in docs}
    qmap = policy_data.get("question_map", [])

    answered_items = [item for item in qmap if item.get("status") == "answered_by_real"]
    assert len(answered_items) >= 20, f"Expected at least 20 answered_by_real items, found {len(answered_items)}"

    for item in answered_items:
        qid = item.get("id")
        quote = item.get("quote", "")
        assert quote, f"Missing quote in answered_by_real item {qid}"

        words = len(quote.split())
        assert words <= 60, f"Quote for {qid} exceeds 60 words limit (has {words} words):\n{quote}"

        norm_quote = normalize(quote)

        # Must be found in at least one of the mapped documents
        found = False
        doc_texts = []
        for did in item.get("doc_ids", []):
            text_path = PROJECT_ROOT / doc_registry[did]["text_path"]
            raw_text = text_path.read_text(errors="ignore")
            doc_texts.append(raw_text)
            if norm_quote in normalize(raw_text):
                found = True
                break

        assert found, f"Verbatim quote for {qid} not found in any mapped doc {item.get('doc_ids')}:\nQuote: {quote}"


def test_needs_reconstruction_appears_in_reconstruction_requirements(policy_data):
    """Test that every item with status 'needs_reconstruction' appears in reconstruction_requirements."""
    qmap = policy_data.get("question_map", [])
    recon = policy_data.get("reconstruction_requirements", {})

    all_recon_mapped_ids = set()
    for rb_name, rb_spec in recon.items():
        all_recon_mapped_ids.update(rb_spec.get("mapped_questions", []))

    needs_recon_items = [item for item in qmap if item.get("status") == "needs_reconstruction"]
    assert len(needs_recon_items) >= 20, f"Expected at least 20 needs_reconstruction items, found {len(needs_recon_items)}"

    for item in needs_recon_items:
        qid = item.get("id")
        assert qid in all_recon_mapped_ids, (
            f"needs_reconstruction item '{qid}' does not appear in mapped_questions "
            f"of any rulebook in reconstruction_requirements!"
        )


def test_reconstruction_requirements_structure(policy_data):
    """Test that all 7 required rulebooks are defined with required clauses and real excerpts."""
    recon = policy_data.get("reconstruction_requirements", {})
    assert set(recon.keys()) == REQUIRED_RULEBOOKS, (
        f"Mismatch in rulebooks. Expected {REQUIRED_RULEBOOKS}, found {set(recon.keys())}"
    )

    docs = policy_data.get("documents", [])
    doc_registry = {d["doc_id"]: d for d in docs}

    for rb_name, rb_spec in recon.items():
        assert rb_spec.get("target_title"), f"Missing target_title in {rb_name}"
        assert rb_spec.get("mapped_questions"), f"Missing mapped_questions in {rb_name}"

        clauses = rb_spec.get("required_clauses", [])
        assert len(clauses) >= 5, f"Rulebook {rb_name} must have at least 5 required clauses, found {len(clauses)}"
        for c in clauses:
            assert c.get("clause_number"), f"Missing clause_number in {rb_name}"
            assert c.get("title"), f"Missing title in {rb_name}"
            assert c.get("requirement"), f"Missing requirement in {rb_name}"

        excerpts = rb_spec.get("real_excerpts", [])
        assert len(excerpts) >= 1, f"Rulebook {rb_name} must contain at least 1 real excerpt"
        for ex in excerpts:
            did = ex.get("doc_id")
            assert did in doc_registry, f"Doc ID {did} in {rb_name} real_excerpts not in registry!"
            assert ex.get("clause_reference"), f"Missing clause_reference in excerpt for {rb_name}"
            assert ex.get("verbatim_quote"), f"Missing verbatim_quote in excerpt for {rb_name}"


def test_valid_statuses(policy_data):
    """Test that all mapped questions carry valid status values."""
    qmap = policy_data.get("question_map", [])
    for item in qmap:
        status = item.get("status")
        assert status in VALID_STATUSES, f"Invalid status '{status}' in item {item.get('id')}"
