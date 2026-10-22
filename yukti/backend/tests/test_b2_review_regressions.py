"""Regression tests for the G4 B2 review (round 1) findings."""

import asyncio
from pathlib import Path
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.brain.compiler import CompileError, CompiledQuery, Compiler
from app.brain.presenter import narrate
from app.brain.query_spec import Filter, Period, QuerySpec, SpecPatch


class _State:
    def __init__(self, hist=None):
        self.turns, self.spec_history, self.last_rows = [], hist or [], []


def test_f1_junior_with_client_spec_patch_never_reaches_planner():
    from app.brain import pipeline
    spec = QuerySpec(metric="headcount", filters=[Filter(field="wc", value="WC-DEL")])
    for persona in ("E2_HR", "E3_FIN", "UNKNOWN"):
        out = asyncio.run(pipeline.run_planner_turn(
            "Show the names", _State([spec.to_contract()]), persona, "t-1", "en", time.perf_counter(),
            patch_override=SpecPatch(grain="row"), base_spec=spec))
        assert out is None, persona


def test_f5_unsupported_filter_falls_back_instead_of_widening():
    c = Compiler()
    with pytest.raises(CompileError):
        c.compile(QuerySpec(metric="pbt_cr", dimensions=["field"], filters=[Filter(field="gender", value="Female")]))
    with pytest.raises(CompileError):  # R2-1: names for a past FY are not available (no silent counts)
        c.compile(QuerySpec(metric="headcount", grain="row", period=Period(fy="FY26"),
                            filters=[Filter(field="station_tenure_years", op=">=", value=5)]))
    with pytest.raises(CompileError):  # as-of view holds executives only
        c.compile(QuerySpec(metric="headcount", period=Period(fy="FY26"),
                            filters=[Filter(field="cadre", value="non_executive"),
                                     Filter(field="station_tenure_years", op=">=", value=5)]))


def _cq(agg, unit, dims):
    return CompiledQuery(sql="", subject="workforce", metric="m", metric_label="Average age", unit=unit,
                         source="generated", tables=["t"], dims=dims, value_columns=["m"], aggregation=agg)


def test_f3_no_sums_of_averages_in_narration():
    spec = QuerySpec(metric="avg_age", dimensions=["wc", "discipline"],
                     filters=[Filter(field="wc", op="in", value=["WC-DEL", "WC-MUM"])])
    rows = [{"work_centre": "Delhi HQ", "discipline": "HR", "m": 40.0},
            {"work_centre": "Delhi HQ", "discipline": "IT", "m": 50.0},
            {"work_centre": "Mumbai High", "discipline": "HR", "m": 45.0}]
    text = narrate(spec, _cq("avg", "years", [("wc", "work_centre"), ("discipline", "discipline")]),
                   ["work_centre", "discipline", "m"], rows)
    assert "90" not in text and "highest IT (50)" in text
    spec2 = QuerySpec(metric="avg_age", dimensions=["discipline"])
    text2 = narrate(spec2, _cq("avg", "years", [("discipline", "discipline")]), ["discipline", "m"], rows[:2])
    assert "across" not in text2  # no total for an average


def test_f6_legacy_marker_blocks_patching_an_old_spec():
    from app.brain import pipeline
    spec = QuerySpec(metric="headcount", filters=[Filter(field="wc", value="WC-DEL")])
    called = {}

    class FakePlanner:
        async def plan(self, q, prev, hist):
            called["prev"] = prev
            from app.brain.planner import Plan
            return Plan(intent="other")

    orig = pipeline.get_planner
    pipeline.get_planner = lambda: FakePlanner()
    try:
        asyncio.run(pipeline.run_planner_turn("only E5 and above", _State([spec.to_contract(), {}]),
                                              "CMD", "t", "en", time.perf_counter()))
    finally:
        pipeline.get_planner = orig
    assert called["prev"] is None


def test_f15_flag_off_data_question_never_awaits_planner(monkeypatch):
    from app import turn_runner as tr
    monkeypatch.setenv("YUKTI_PLANNER", "0")
    r = tr.AgentTurnRunner(model_name="gemini-2.5-flash")

    async def boom(*a, **k):
        raise AssertionError("planner must not run when YUKTI_PLANNER=0")

    async def no_events(*a, **k):
        if False:
            yield None

    monkeypatch.setattr(tr, "run_planner_turn", boom)
    monkeypatch.setattr(r.runner, "run_async", no_events)
    import app.router as router_mod

    class R:
        def route(self, **k):
            return {"route": "live_nl_sql", "query_id": None, "score": 0.0, "extracted_params": {}, "elapsed_ms": 0}

    monkeypatch.setattr(tr, "get_semantic_router", lambda: R())
    res = asyncio.run(r.execute_turn_async("Which fields lost money in FY26?", session_id="f15", persona="CMD"))
    assert "query_spec" not in res


def test_f12_limits_are_bounded():
    c = Compiler()
    row = c.compile(QuerySpec(metric="headcount", grain="row", limit=10**9))
    assert row.sql.rstrip().endswith("LIMIT 2000")
    agg = c.compile(QuerySpec(metric="headcount", dimensions=["wc"], limit=10**9))
    assert agg.sql.rstrip().endswith("LIMIT 1000")


def test_f8_capex_vs_reserves_reproduces_certified_c7_answer_key():
    """Live (BigQuery): the template mirrors certified C7 — answer key: Eastern Offshore ₹48,955 cr, 32.1 %."""
    c = Compiler()
    cq = c.compile(QuerySpec(metric="capex_vs_reserves"))
    res = c._run_sync(cq.sql)
    top = res.rows[0]
    assert top["asset"] == "WC-EAS" and round(top["capex_cr"]) == 48955 and top["pct_of_capex"] == 32.1
    second = res.rows[1]
    assert second["asset"] == "WC-MUM" and round(second["capex_cr"]) == 26473
