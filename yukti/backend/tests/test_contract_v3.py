"""Unit tests for Answer Contract v3 consolidation (Packet P3.1, SPEC-03 §5).

Verifies:
1. All v3 fixtures in `yukti/contracts/fixtures/v3_*.json` validate cleanly against
   `yukti/contracts/answer_contract.schema.json`.
2. Backward compatibility: v1 (`contract_version` omitted / `1`) and v2 (`contract_version: 2`)
   payloads validate cleanly, including all 11 personas (`SPEC-06`).
3. Ledger consolidation: every `SPEC-03 §5.1` ledger key (`clarify`, `actions`, `artifacts`,
   `email_draft`, `proposed_action`, `job`, `provenance`, and `visual.type` values `statement`,
   `sensitivity_grid`, `tornado`, `dcf_model`, `actions`, `email_draft`) appears once in the schema
   and validates.
4. Invalid payloads (missing `proposed_action.id`, bad `job.status`, bad `persona`, bad `contract_version`)
   fail schema validation as expected.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest

from app.answer_composer import (
    _VALID_PERSONAS,
    _VALID_VISUAL_TYPES,
    get_contract_validator,
    validate_and_repair_contract,
)
from app.config import CONTRACT_SCHEMA_PATH

FIXTURES_DIR = CONTRACT_SCHEMA_PATH.parent / "fixtures"

V3_FIXTURE_FILES = [
    "v3_proposal.json",
    "v3_job_running.json",
    "v3_job_succeeded_dcf.json",
    "v3_clarify.json",
    "v3_actions.json",
    "v3_provenance_local_snapshot.json",
]


def _load_schema() -> dict:
    return json.loads(CONTRACT_SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("fixture_name", V3_FIXTURE_FILES)
def test_v3_fixtures_validate(fixture_name: str) -> None:
    path = FIXTURES_DIR / fixture_name
    assert path.exists(), f"Missing fixture {path}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    validator = get_contract_validator()
    validator.validate(payload)


def test_v1_and_v2_backward_compatibility() -> None:
    validator = get_contract_validator()
    base_v1 = {
        "turn_id": "turn-v1-001",
        "language": "en",
        "persona": "CMD",
        "spoken_summary": "Total active headcount is 25,642.",
        "display_text": "ONGC Active Headcount: 25,642.",
        "visual": {"type": "kpi", "mode": "replace", "kpis": [{"label": "Headcount", "value": 25642}]},
        "insights": ["Headcount is stable."],
        "sources": [{"kind": "data", "object": "v_emp_current"}],
        "suggestions": ["By work centre"],
        "access": {"status": "allowed"},
        "export_options": ["pdf"],
        "status_events": ["Completed"],
    }
    validator.validate(base_v1)

    v1_explicit = copy.deepcopy(base_v1)
    v1_explicit["contract_version"] = 1
    validator.validate(v1_explicit)

    v2_payload = copy.deepcopy(base_v1)
    v2_payload["contract_version"] = 2
    v2_payload["query_spec"] = {
        "version": 1,
        "domain": "hr",
        "metric": "headcount",
        "aggregation": "count",
        "grain": "aggregate",
    }
    validator.validate(v2_payload)


@pytest.mark.parametrize(
    "persona",
    [
        "CMD",
        "DIR_HR",
        "DIR_FIN",
        "E1_HR",
        "E2_HR",
        "E3_HR",
        "E4_HR",
        "E1_FIN",
        "E2_FIN",
        "E3_FIN",
        "E4_FIN",
    ],
)
def test_all_11_personas_validate(persona: str) -> None:
    assert persona in _VALID_PERSONAS
    validator = get_contract_validator()
    payload = json.loads((FIXTURES_DIR / "v3_provenance_local_snapshot.json").read_text(encoding="utf-8"))
    payload["persona"] = persona
    validator.validate(payload)


def test_ledger_rows_consolidated_in_schema() -> None:
    schema = _load_schema()
    props = schema["properties"]
    assert schema["properties"]["contract_version"]["enum"] == [1, 2, 3]
    for top_key in (
        "clarify",
        "actions",
        "artifacts",
        "email_draft",
        "proposed_action",
        "job",
        "provenance",
    ):
        assert top_key in props, f"Missing top-level ledger property {top_key}"

    visual_types = set(props["visual"]["properties"]["type"]["enum"])
    for vtype in (
        "statement",
        "sensitivity_grid",
        "tornado",
        "dcf_model",
        "actions",
        "email_draft",
    ):
        assert vtype in visual_types, f"Missing visual.type enum {vtype}"
        assert vtype in _VALID_VISUAL_TYPES


def test_invalid_proposed_action_missing_id_fails() -> None:
    validator = get_contract_validator()
    payload = json.loads((FIXTURES_DIR / "v3_proposal.json").read_text(encoding="utf-8"))
    del payload["proposed_action"]["id"]
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(payload)


def test_invalid_job_status_fails() -> None:
    validator = get_contract_validator()
    payload = json.loads((FIXTURES_DIR / "v3_job_running.json").read_text(encoding="utf-8"))
    payload["job"]["status"] = "bogus_status"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(payload)


def test_invalid_contract_version_fails() -> None:
    validator = get_contract_validator()
    payload = json.loads((FIXTURES_DIR / "v3_proposal.json").read_text(encoding="utf-8"))
    payload["contract_version"] = 99
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(payload)


def test_validate_and_repair_preserves_v3_visual_types() -> None:
    payload = json.loads((FIXTURES_DIR / "v3_job_succeeded_dcf.json").read_text(encoding="utf-8"))
    repaired = validate_and_repair_contract(payload)
    assert repaired["visual"]["type"] == "dcf_model"
    assert repaired["contract_version"] == 3
