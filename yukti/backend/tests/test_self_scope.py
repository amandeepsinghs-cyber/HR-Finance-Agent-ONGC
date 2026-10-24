"""P2H.1 / SPEC-06 §4.5 & §8 / BUG-07: @self_emp_id parameterisation, 8 certified self queries, and zero cross-employee leakage."""

from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Any, Dict, List

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.access_control import ALL_PERSONAS_ORDERED
from app.auth import PERSONA_DIRECTORY
from app.brain.compiler import compile_spec
from app.brain.pipeline import _planner_allowed
from app.brain.planner import Planner
from app.brain.query_spec import QuerySpec
from app.tools import certified_query as cq_mod
from app.tools.certified_query import get_certified_entry, resolve_self_emp_id, run_certified_query

BACKEND_ROOT = Path(__file__).resolve().parent.parent
CERT_LIB_MAIN = BACKEND_ROOT / "certified" / "library.yaml"
CERT_LIB_BRAIN = BACKEND_ROOT / "app" / "brain" / "certified" / "library.yaml"

SELF_QUERY_IDS = [
    "my_payslip",
    "my_pay_components_fy",
    "my_leave_balance",
    "my_leave_ledger",
    "my_postings",
    "my_station_tenure",
    "my_apar",
    "my_entitlements",
]

LEGACY_SELF_IDS = ["E1", "E2", "E3", "E6"]


def test_zero_hardcoded_emp_id_literals_in_certified_libraries():
    """SPEC-06 §4.5 / M2 CI grep gate: 0 literal EMP-XXXXXX anywhere in certified/library.yaml and app/brain/certified/library.yaml."""
    pat = re.compile(r"EMP-[0-9]{4,6}", re.IGNORECASE)
    for path in (CERT_LIB_MAIN, CERT_LIB_BRAIN):
        assert path.exists(), f"Missing {path}"
        text = path.read_text(encoding="utf-8")
        matches = pat.findall(text)
        assert not matches, f"Hardcoded emp_id literal found in {path}: {matches}"


@pytest.mark.parametrize("qid", SELF_QUERY_IDS + LEGACY_SELF_IDS)
def test_certified_self_queries_have_self_emp_id_placeholder(qid: str):
    entry = get_certified_entry(qid)
    assert entry is not None, f"Missing certified self query {qid}"
    sql = entry["parameterized_sql"]
    assert "@self_emp_id" in sql, f"{qid} SQL does not bind @self_emp_id"
    assert "EMP-102451" not in sql, f"{qid} SQL still contains hardcoded EMP-102451"


@pytest.mark.parametrize("persona", list(ALL_PERSONAS_ORDERED))
@pytest.mark.parametrize("qid", SELF_QUERY_IDS)
def test_11_personas_x_8_self_queries_bind_own_emp_id(monkeypatch, persona: str, qid: str):
    """SPEC-06 §8: 11 personas × 8 self queries = 88 cases bind @self_emp_id = principal.emp_id with 0 cross-employee rows."""
    captured: Dict[str, Any] = {}
    expected_emp_id = PERSONA_DIRECTORY[persona]["emp_id"]

    class _FakeField:
        def __init__(self, name: str):
            self.name = name

    class _FakeIter:
        schema = [_FakeField("emp_id"), _FakeField("persona_check")]

        def __iter__(self):
            return iter([{"emp_id": captured["self_emp_id"], "persona_check": persona}])

    class _FakeJob:
        def result(self):
            return _FakeIter()

    class _FakeBQClient:
        def __init__(self, *args, **kwargs):
            pass

        def query(self, sql: str, job_config: Any = None):
            captured["sql"] = sql
            params = {p.name: p.value for p in (job_config.query_parameters or [])}
            captured["params"] = params
            captured["self_emp_id"] = params.get("self_emp_id")
            return _FakeJob()

    monkeypatch.setattr(cq_mod.bigquery, "Client", _FakeBQClient)
    # Clear tool cache for clean per-case capture
    cq_mod.get_tool_cache().clear()

    # Attempt parameter spoofing via caller params={"self_emp_id": "EMP-102451"} — must be ignored!
    res = run_certified_query(qid, params={"self_emp_id": "EMP-102451"}, persona=persona)
    assert "@self_emp_id" in captured["sql"]
    assert captured["self_emp_id"] == expected_emp_id
    assert res["rows"][0]["emp_id"] == expected_emp_id
    if persona != "E2_HR":
        assert captured["self_emp_id"] != "EMP-102451"
        assert all(r.get("emp_id") != "EMP-102451" for r in res["rows"])


@pytest.mark.parametrize("persona", list(ALL_PERSONAS_ORDERED))
def test_compiler_injects_self_emp_id_predicate_and_scalar_param(persona: str):
    """SPEC-06 §4.5: compile_spec with self_scope=True injects `emp_id = @self_emp_id` and binds ScalarQueryParameter."""
    emp_id = resolve_self_emp_id(persona)
    assert emp_id == PERSONA_DIRECTORY[persona]["emp_id"]
    spec = QuerySpec(domain="hr", metric="headcount", grain="row", self_scope=True)
    compiled = compile_spec(spec, self_emp_id=emp_id)
    assert "emp_id = @self_emp_id" in compiled.sql
    assert compiled.data_classes == ["self"]
    assert compiled.self_emp_id == emp_id
    param_map = {p.name: (p.type_, p.value) for p in compiled.params}
    assert param_map.get("self_emp_id") == ("STRING", emp_id)


@pytest.mark.parametrize(
    "utterance",
    [
        "What is my leave balance?",
        "Show my payslip for September",
        "How long have I been posted in Delhi?",
        "Show my APAR history",
        "मेरी छुट्टी कितनी बची है?",
        "Mera salary slip dikhao",
    ],
)
def test_planner_marks_possessive_queries_as_self_scope_and_pipeline_allows_my(utterance: str):
    """SPEC-06 §4.5: _PERSON_RE no longer blocks 'my', and Planner.to_plan sets spec.self_scope=True."""
    assert _planner_allowed(utterance, "E3_FIN") is True
    plan = Planner().to_plan(utterance, {}, prev=None)
    assert plan.intent == "data"
    assert plan.spec is not None
    assert plan.spec.self_scope is True
    compiled = compile_spec(plan.spec, self_emp_id=PERSONA_DIRECTORY["E3_FIN"]["emp_id"])
    assert "emp_id = @self_emp_id" in compiled.sql
    assert compiled.data_classes == ["self"]


def test_person_re_still_blocks_explicit_employee_number():
    assert _planner_allowed("Show details of employee 104523", "E2_HR") is False


@pytest.mark.parametrize("bad_persona", [None, "", "   ", "UNKNOWN", "E5_HR", "DEMO_ADMIN", "INTERN"])
def test_m2_resolve_self_emp_id_and_run_certified_query_reject_unknown_or_empty_persona(bad_persona):
    """M2: resolve_self_emp_id and run_certified_query on self queries raise UnknownPersona when persona is missing/unknown."""
    from app.access_control import UnknownPersona

    with pytest.raises(UnknownPersona):
        resolve_self_emp_id(bad_persona)
    with pytest.raises(UnknownPersona):
        run_certified_query("my_payslip", persona=bad_persona)


def test_m1_agent_tool_wrapper_fails_closed_without_principal_and_binds_active_principal(monkeypatch):
    """M1: agent.run_certified_query fails closed without an active Principal and binds distinct emp_ids per persona."""
    import asyncio
    from app import agent as agent_mod
    from app.auth import principal_for_persona, reset_active_principal, set_active_principal

    captured_calls: List[Dict[str, Any]] = []

    def _fake_exec(query_id: str, params=None, persona=None, self_emp_id=None):
        captured_calls.append({"query_id": query_id, "persona": persona, "self_emp_id": self_emp_id})
        return {"type": "certified_query_result", "query_id": query_id, "persona": persona, "self_emp_id": self_emp_id}

    monkeypatch.setattr(agent_mod, "execute_certified_query", _fake_exec)

    # 1. Without a bound server Principal -> fail closed with E-AUTH (never defaults to CMD / EMP-000001)
    res_no_principal = asyncio.run(agent_mod.run_certified_query("my_payslip"))
    assert res_no_principal["type"] == "error"
    assert res_no_principal["code"] == "E-AUTH"
    assert len(captured_calls) == 0

    # 2. Bound to E1_HR -> passes E1_HR / EMP-100151
    tok1 = set_active_principal(principal_for_persona("E1_HR"))
    try:
        res_e1 = asyncio.run(agent_mod.run_certified_query("my_payslip"))
    finally:
        reset_active_principal(tok1)

    # 3. Bound to E3_FIN -> passes E3_FIN / EMP-100146
    tok2 = set_active_principal(principal_for_persona("E3_FIN"))
    try:
        res_e3 = asyncio.run(agent_mod.run_certified_query("my_payslip"))
    finally:
        reset_active_principal(tok2)

    assert res_e1["persona"] == "E1_HR" and res_e1["self_emp_id"] == "EMP-100151"
    assert res_e3["persona"] == "E3_FIN" and res_e3["self_emp_id"] == "EMP-100146"
    assert res_e1["self_emp_id"] != res_e3["self_emp_id"]
    assert res_e1["self_emp_id"] != "EMP-000001"
    assert res_e3["self_emp_id"] != "EMP-000001"

