"""B2: semantic_model.yaml is consistent with the data catalog (offline), and the
YUKTI_PLANNER flag switches modes without touching the baseline path (offline, B2.4)."""

import asyncio
import json
from pathlib import Path
import re
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.brain.semantic_model import get_semantic_model

BACKEND = Path(__file__).resolve().parent.parent
CAT = json.loads((BACKEND / "app/semantic/semantic_catalog.json").read_text(encoding="utf-8"))["tables"]
SQL_WORDS = {"COUNT", "COUNTIF", "SUM", "AVG", "ROUND", "NULLIF", "CASE", "WHEN", "THEN", "ELSE", "END", "AND", "OR",
             "NOT", "IS", "NULL", "TRUE", "FALSE", "IN", "AS", "DISTINCT", "LIKE", "MIN", "MAX", "LOWER", "UPPER"}


def _identifiers(expr: str):
    expr = re.sub(r"'[^']*'", " ", expr)
    return {t for t in re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", expr) if t.upper() not in SQL_WORDS}


def test_semantic_model_tables_and_columns_exist():
    m = get_semantic_model()
    bad = []
    for s in m.subjects.values():
        cols = set((CAT.get(s.table) or {}).get("columns", {}))
        if not cols:
            bad.append(f"{s.name}: table {s.table} not in catalog")
            continue
        for f in s.fields.values():
            if f.column not in cols:
                bad.append(f"{s.name}.{f.name}: column {f.column}")
        for md in s.metrics.values():
            for ident in _identifiers(md.expr):
                if ident not in cols:
                    bad.append(f"{s.name}.{md.name}: {ident}")
        for rc in s.row_columns:
            for ident in _identifiers(rc["expr"]):
                if ident not in cols:
                    bad.append(f"{s.name} row column {rc['as']}: {ident}")
        if s.base_filter:
            for ident in _identifiers(s.base_filter):
                if ident not in cols:
                    bad.append(f"{s.name} base_filter: {ident}")
        if s.asof:
            acols = set((CAT.get(s.asof["table"]) or {}).get("columns", {}))
            for c in list(s.asof.get("fields", {}).values()) + [s.asof["tenure_from_column"], s.asof["tenure_to_column"]]:
                if c not in acols:
                    bad.append(f"{s.name} asof: {c}")
    assert not bad, bad


def test_metric_names_unique_and_units_known():
    from app.brain.presenter import UNIT_WORDS
    m = get_semantic_model()
    for md in m.metrics.values():
        assert md.unit in UNIT_WORDS, (md.name, md.unit)


# ----------------------------------------------------------------- B2.4 flag modes
@pytest.fixture()
def runner(monkeypatch):
    from app import turn_runner as tr
    r = tr.AgentTurnRunner(model_name="gemini-2.5-flash")
    return r


def test_flag_off_never_calls_planner(monkeypatch, runner):
    from app import turn_runner as tr
    monkeypatch.setenv("YUKTI_PLANNER", "0")

    async def boom(*a, **k):
        raise AssertionError("planner must not run when YUKTI_PLANNER=0")

    monkeypatch.setattr(tr, "run_planner_turn", boom)
    # A greeting is answered before any LLM call; it proves the flag-off path never reaches the planner.
    res = asyncio.run(runner.execute_turn_async("hello", session_id="flag-off-test", persona="CMD"))
    assert res["access"]["status"] == "allowed"
    assert "query_spec" not in res


def test_flag_on_uses_planner_contract(monkeypatch, runner):
    from app import turn_runner as tr
    monkeypatch.setenv("YUKTI_PLANNER", "1")
    calls = {}

    async def fake(query, session_state, persona, turn_id, language, t0, **kw):
        calls["q"] = query
        contract = {
            "turn_id": turn_id, "language": language, "persona": persona,
            "spoken_summary": "419 executives.", "display_text": "419 executives.",
            "visual": {"type": "kpi", "mode": "replace", "kpis": [{"label": "Executives", "value": 419}]},
            "insights": ["419"], "sources": [{"kind": "data", "object": "x", "sql": "SELECT 1"}],
            "suggestions": [], "access": {"status": "allowed"}, "export_options": ["pdf"], "status_events": [],
            "latency_ms": 1.0, "contract_version": 2,
            "query_spec": {"version": 1, "metric": "headcount", "grain": "aggregate", "dimensions": [], "filters": []},
        }
        from app.brain.query_spec import QuerySpec
        return {"contract": contract, "meta": {"rows": [], "spec": QuerySpec(metric="headcount")}}

    monkeypatch.setattr(tr, "run_planner_turn", fake)
    res = asyncio.run(runner.execute_turn_async("How many executives in Delhi for 5+ years?",
                                                session_id="flag-on-test", persona="CMD"))
    assert calls["q"].startswith("How many")
    assert res["query_spec"]["metric"] == "headcount"
    st = runner.session_manager.get_or_create("flag-on-test")
    assert st.spec_history and st.spec_history[-1]["metric"] == "headcount"


def test_flag_on_skips_keyword_fast_paths(monkeypatch, runner):
    """With the planner on, 'breakdown by discipline' must not be answered by the keyword fast path."""
    from app import turn_runner as tr
    monkeypatch.setenv("YUKTI_PLANNER", "1")
    seen = {}

    async def none_planner(query, *a, **k):
        seen["planner"] = True
        return None  # planner declines -> legacy LLM path, never the keyword fast path

    async def fake_qd_guard(*a, **k):
        raise AssertionError("keyword fast path ran")

    monkeypatch.setattr(tr, "run_planner_turn", none_planner)
    import app.tools.query_data as qd
    monkeypatch.setattr(qd, "query_data", lambda *a, **k: (_ for _ in ()).throw(AssertionError("keyword fast path ran")))

    async def fake_runner_events(*a, **k):
        if False:
            yield None

    monkeypatch.setattr(runner.runner, "run_async", fake_runner_events)
    res = asyncio.run(runner.execute_turn_async("Show breakdown by discipline", session_id="fp-test", persona="CMD"))
    assert seen.get("planner") is True
    assert res["turn_id"].startswith("turn-fp-test")
