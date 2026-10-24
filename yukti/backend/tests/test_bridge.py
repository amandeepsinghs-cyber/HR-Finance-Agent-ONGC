"""P4.1 Backend Tests: Signed P&L Waterfall Bridge, Error Refusals, and Re-Plot Integrity.

Covers SPEC-09 §4.3, BEH-04.10–.16, BEH-04.20–.21, BEH-07.34, BUG-08, BUG-09, BUG-22,
and diag_C probe §A3 reproduction.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
YUKTI_ROOT = BACKEND_ROOT.parent
CONTRACTS_DIR = YUKTI_ROOT / "contracts"
BRIDGE_FIXTURES_DIR = CONTRACTS_DIR / "fixtures" / "bridge"
LEGACY_PNL_JSON = YUKTI_ROOT.parent / "financial_build" / "data" / "ongc_10yr_schedule_iii_lines.json"

sys.path.insert(0, str(BACKEND_ROOT))

from app.brain.bridge import (  # noqa: E402
    BRIDGE_TOLERANCE_CR,
    BridgeError,
    BridgeOk,
    bridge,
    bridge_class_of,
    single_value_error,
)
from app.brain.compiler import CompiledQuery, QueryResult  # noqa: E402
from app.brain.presenter import build_visual  # noqa: E402
from app.brain.query_spec import Period, QuerySpec  # noqa: E402
from app.session_memory import get_session_manager  # noqa: E402
from app.turn_runner import AgentTurnRunner  # noqa: E402

FALSE_SUCCESS_RE = re.compile(r"I've\s+(?:replotted|switched)|switched\s+the\s+(?:screen\s+)?view", re.I)


def _load_pnl_fixture() -> Dict[str, Any]:
    with (BRIDGE_FIXTURES_DIR / "pnl_fixture_synthetic.json").open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_classes() -> Dict[str, Any]:
    with (CONTRACTS_DIR / "statement_line_classes.json").open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _rows_of(stmt: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for sec in stmt.get("sections") or []:
        rows.extend(sec.get("rows") or [])
    return rows


# ---------------------------------------------------------------------------
# 1. Shared synthetic P&L fixture: 5 FYs x 2 granularities = 10 cases
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fy", ["FY26", "FY25", "FY24", "FY23", "FY22"])
@pytest.mark.parametrize("granularity", ["standard", "full"])
def test_pnl_fixture_10_cases_land_on_pat_within_tolerance(fy: str, granularity: str) -> None:
    pnl = _load_pnl_fixture()
    classes_cfg = _load_classes()
    rows = _rows_of(pnl)
    res = bridge(pnl, period=fy, granularity=granularity)  # type: ignore[arg-type]
    assert isinstance(res, BridgeOk), f"Expected BridgeOk for {fy} ({granularity}), got {res}"
    assert res.ok is True

    pat_row = next(r for r in rows if classes_cfg["classes"].get(r["line_code"]) == "end")
    reported_pat = float(pat_row["values"][fy])

    last_bar = res.bars[-1]
    assert last_bar.type == "total"
    assert abs(last_bar.value - reported_pat) <= BRIDGE_TOLERANCE_CR
    assert last_bar.value == reported_pat

    # Walk the bars: running sum of deltas from start reproduces every subtotal and PAT within ₹0.5 cr
    running = res.bars[0].value
    assert res.bars[0].type == "total"
    for b in res.bars[1:]:
        assert b.type in ("total", "delta")
        if b.type == "delta":
            running += b.value
        else:
            assert abs(running - b.value) <= BRIDGE_TOLERANCE_CR, f"{b.label}: {running} vs {b.value}"
            running = b.value

    # Never invent EBITDA, OPEX & Levies, or unsigned Others
    input_labels = {r["label"] for r in rows}
    for b in res.bars:
        assert not (
            re.search(r"ebitda|opex\s*&\s*levies", b.label, re.I) and b.label not in input_labels
        ), f"Invented bar found: {b.label}"
        assert not re.match(r"^others(\s*\(|$)", b.label, re.I), f"Unsigned 'Others' bar found: {b.label}"

    if granularity == "full":
        assert not any(b.merged for b in res.bars), "full granularity must never merge rows"
    else:
        merged_bars = [b for b in res.bars if b.merged]
        assert len(merged_bars) >= 1, "standard granularity must merge <2% deduct rows"
        for mb in merged_bars:
            assert mb.label == classes_cfg["merged_deduct_label"]
            assert mb.value < 0
        idx_merged = next(i for i, b in enumerate(res.bars) if b.merged)
        assert res.bars[idx_merged + 1].type == "total", "merged bar must be emitted immediately before subtotal"


# ---------------------------------------------------------------------------
# 2. Legacy 10-year Schedule III P&L (FY17..FY26) closes to PAT with 0 plug
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not LEGACY_PNL_JSON.exists(), reason="financial_build P&L JSON not present")
@pytest.mark.parametrize("fy", [f"FY{y}" for y in range(17, 27)])
def test_legacy_10yr_schedule_iii_pnl_bridge_closes_to_pat(fy: str) -> None:
    data = json.loads(LEGACY_PNL_JSON.read_text(encoding="utf-8"))
    fy_rows = [r for r in data if r.get("fiscal_year") == fy]
    assert fy_rows, f"No rows for {fy}"
    pat_val = next(
        float(r.get("amount_cr") if r.get("amount_cr") is not None else r["amount_inr_cr"])
        for r in fy_rows
        if r["line_code"] == "pat_inr_cr"
    )

    res = bridge(fy_rows, period=fy, granularity="standard")
    assert isinstance(res, BridgeOk), f"Bridge failed for {fy}: {res}"
    assert res.bars[-1].type == "total"
    assert abs(res.bars[-1].value - pat_val) <= BRIDGE_TOLERANCE_CR
    assert 10 <= len(res.bars) <= 15
    assert not any("ebitda" in b.label.lower() for b in res.bars), "EBITDA memo row must be skipped in Schedule III bridge"


# ---------------------------------------------------------------------------
# 3. 5 Shared Error Fixtures -> exact BridgeError codes & honest copy
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "fixture_name",
    [
        "error_missing_start.json",
        "error_missing_end.json",
        "error_subtotal_mismatch.json",
        "error_pat_mismatch.json",
        "error_single_value.json",
    ],
)
def test_error_fixtures_return_expected_bridge_error(fixture_name: str) -> None:
    fx = json.loads((BRIDGE_FIXTURES_DIR / fixture_name).read_text(encoding="utf-8"))
    expected = fx["expected_error"]
    res = bridge(fx, period=(fx.get("periods") or [None])[0])
    assert isinstance(res, BridgeError), f"Expected BridgeError for {fixture_name}, got {res}"
    assert res.ok is False
    assert res.code == expected["code"]
    assert expected["reason_contains"].lower() in res.reason.lower(), f"Reason mismatch: {res.reason}"

    msg_en = res.message(lang="en")
    msg_hi = res.message(lang="hi")
    assert msg_en and not FALSE_SUCCESS_RE.search(msg_en)
    assert msg_hi and not FALSE_SUCCESS_RE.search(msg_hi)


# ---------------------------------------------------------------------------
# 4. diag_C Probe §A3 Reproduction: FY25 P&L -> "Show this as a waterfall chart"
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not LEGACY_PNL_JSON.exists(), reason="financial_build P&L JSON not present")
def test_diag_c_probe_a3_fy25_pnl_replot_as_waterfall() -> None:
    from app.brain.compiler import get_compiler

    data = json.loads(LEGACY_PNL_JSON.read_text(encoding="utf-8"))
    fy25_rows = [
        {
            **r,
            "line_item": r.get("line_item") or r.get("line_name"),
            "amount_cr": r.get("amount_cr") if r.get("amount_cr") is not None else r.get("amount_inr_cr"),
            "prior_fy_cr": r.get("prior_fy_cr") if r.get("prior_fy_cr") is not None else r.get("prior_fy_inr_cr"),
            "yoy_delta_cr": r.get("yoy_delta_cr") if r.get("yoy_delta_cr") is not None else r.get("yoy_delta_inr_cr"),
        }
        for r in data
        if r.get("fiscal_year") == "FY25"
    ]
    cols = list(fy25_rows[0].keys())

    spec = QuerySpec(domain="finance", metric="pnl_statement", dimensions=["line_item"], period=Period(fy="FY25"))
    compiled = get_compiler().compile(spec)
    vis = build_visual(
        spec=spec,
        compiled=compiled,
        columns=cols,
        rows=fy25_rows,
        chart_kind=None,
        title="ONGC Statement of Profit & Loss · FY25",
        subtitle="FY25",
        mode="replace",
    )
    # Table-first default on initial P&L turn, with line_code preserved for TS/py replot
    assert vis["type"] == "table"
    assert "line_code" in vis["table"]["columns"]

    # Record turn in session and run "Show this as a waterfall chart"
    sm = get_session_manager()
    session_id = "test-diag-c-a3-fy25"
    st = sm.get_or_create(session_id, persona="CMD", language="en")
    st.record_turn(
        {
            "turn_id": "turn-001",
            "language": "en",
            "persona": "CMD",
            "spoken_summary": "FY25 P&L is on screen.",
            "display_text": "FY25 P&L is on screen.",
            "visual": vis,
            "insights": ["FY25 PAT ₹36,236.20 Cr"],
            "sources": [{"kind": "data", "object": "hrfin_gold"}],
            "suggestions": [],
            "access": {"status": "allowed"},
            "export_options": ["pdf"],
            "status_events": [],
        },
        user_query="Show me ONGC's FY25 P&L statement",
        all_rows=fy25_rows,
    )

    runner = AgentTurnRunner.__new__(AgentTurnRunner)
    runner.session_manager = sm

    replot_contract = asyncio.run(
        runner._execute_turn_inner(
            query="Show this as a waterfall chart",
            session_id=session_id,
            persona="CMD",
            language="en",
        )
    )
    r_vis = replot_contract["visual"]
    assert r_vis["type"] == "chart"
    chart = r_vis["chart"]
    assert chart["kind"] == "waterfall"
    bars = chart["data"]
    expected_pat = next(r["amount_cr"] for r in fy25_rows if r["line_code"] == "pat_inr_cr")
    assert 10 <= len(bars) <= 15, f"Expected 10-15 bridge bars (never 23 raw lines), got {len(bars)}: {bars}"
    assert all(b.get("type") in ("total", "delta") for b in bars)
    assert bars[0]["type"] == "total" and abs(bars[0]["amount_cr"] - 137846.0) <= 1.0
    assert bars[-1]["type"] == "total" and abs(bars[-1]["amount_cr"] - expected_pat) <= 0.5

    # Also verify statement visual re-plot on shared FY25 fixture (PAT = ₹36,236.20 cr)
    pnl_fx = _load_pnl_fixture()
    st_fx = sm.get_or_create("test-diag-c-a3-statement-fy25", persona="CMD", language="en")
    st_fx.record_turn(
        {
            "turn_id": "turn-001",
            "language": "en",
            "persona": "CMD",
            "spoken_summary": "FY25 P&L statement is on screen.",
            "display_text": "FY25 P&L statement is on screen.",
            "visual": {
                "type": "statement",
                "mode": "replace",
                "title": "ONGC FY25 P&L Statement",
                "statement": {**pnl_fx, "periods": ["FY25"]},
            },
            "insights": ["FY25 PAT ₹36,236.20 Cr"],
            "sources": [{"kind": "data", "object": "hrfin_gold"}],
            "suggestions": [],
            "access": {"status": "allowed"},
            "export_options": ["pdf"],
            "status_events": [],
        },
        user_query="Show me ONGC's FY25 P&L statement",
    )
    replot_fx = asyncio.run(
        runner._execute_turn_inner(
            query="Show this as a waterfall chart",
            session_id="test-diag-c-a3-statement-fy25",
            persona="CMD",
            language="en",
        )
    )
    fx_bars = replot_fx["visual"]["chart"]["data"]
    assert all(b.get("type") in ("total", "delta") for b in fx_bars)
    assert fx_bars[0]["type"] == "total" and abs(fx_bars[0]["amount_cr"] - 137846.29) <= 0.5
    assert fx_bars[-1]["type"] == "total" and abs(fx_bars[-1]["amount_cr"] - 35610.32) <= 0.5

    # Switching back to table restores the statement table
    back_contract = asyncio.run(
        runner._execute_turn_inner(
            query="Show as a table",
            session_id=session_id,
            persona="CMD",
            language="en",
        )
    )
    assert back_contract["visual"]["type"] == "table"
    assert len(back_contract["visual"]["table"]["rows"]) == len(fy25_rows)


# ---------------------------------------------------------------------------
# 5. Single-value KPI waterfall refusal (EN + HI + 3 fedback2 phrasings)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "utterance,expected_lang",
    [
        ("Can you express this as a waterfall?", "en"),
        ("Show this as a waterfall", "en"),
        ("Ankleshwar का टोटल रेवेन्यू का वॉटरफॉल चार्ट बना दो।", "hi"),
        ("नहीं, यह वॉटरफॉल चार्ट्स दिख नहीं रहा है।", "hi"),
        ("नहीं बदला गया।", "hi"),
    ],
)
def test_single_value_kpi_waterfall_refusal_no_false_switch(utterance: str, expected_lang: str) -> None:
    sm = get_session_manager()
    session_id = f"test-single-val-{ abs(hash(utterance)) }"
    st = sm.get_or_create(session_id, persona="CMD", language=expected_lang)
    kpi_vis = {
        "type": "kpi",
        "mode": "replace",
        "title": "Ankleshwar Asset: FY26 Gross Revenue",
        "kpis": [{"label": "Gross Revenue (FY26)", "value": 3098.48, "unit": "₹ crore"}],
        "table": {
            "columns": ["asset", "gross_revenue_cr"],
            "rows": [{"asset": "Ankleshwar Asset", "gross_revenue_cr": 3098.48}],
        },
    }
    st.active_entities["wc_name"] = "Ankleshwar"
    st.record_turn(
        {
            "turn_id": "turn-001",
            "language": expected_lang,
            "persona": "CMD",
            "spoken_summary": "Ankleshwar Asset gross revenue in FY26 was ₹3,098.48 crore.",
            "display_text": "Ankleshwar Asset gross revenue in FY26 was ₹3,098.48 crore.",
            "visual": kpi_vis,
            "insights": ["Ankleshwar FY26 revenue: ₹3,098.48 Cr"],
            "sources": [{"kind": "data", "object": "hrfin_gold"}],
            "suggestions": [],
            "access": {"status": "allowed"},
            "export_options": ["pdf"],
            "status_events": [],
        },
        user_query="अंकलेश्वर एसेट का टोटल रेवेन्यू कितना रहा था फाइनेंशियल ईयर 26 में?",
        all_rows=[{"asset": "Ankleshwar Asset", "gross_revenue_cr": 3098.48}],
    )

    runner = AgentTurnRunner.__new__(AgentTurnRunner)
    runner.session_manager = sm

    contract = asyncio.run(
        runner._execute_turn_inner(
            query=utterance,
            session_id=session_id,
            persona="CMD",
            language=expected_lang,
        )
    )
    spoken = contract["spoken_summary"]
    assert not FALSE_SUCCESS_RE.search(spoken), f"False success message emitted: {spoken}"
    assert "ui_action" not in contract, "Refused re-plot must not emit a ui_action"
    assert contract["visual"]["type"] == "kpi", "Previous KPI visual must remain unchanged on refusal"
    assert any("Ankleshwar" in s for s in contract.get("suggestions", [])), (
        f"Expected Ankleshwar revenue trend suggestion chip, got {contract.get('suggestions')}"
    )


# ---------------------------------------------------------------------------
# 6. G4 r2 regressions: M1, M2 (BEH-04.12), M3, S3, S4
# ---------------------------------------------------------------------------
def test_m1_multi_row_non_kpi_visual_not_hijacked_into_unsigned_waterfall(monkeypatch: pytest.MonkeyPatch) -> None:
    """M1: With a 4-asset bar chart on screen, a new single-metric waterfall query must NOT hijack
    set_chart_kind to re-plot the 4-asset bar chart as an unsigned waterfall, and an explicit
    'Show this as a waterfall' on the 4-asset bar chart must refuse honestly without a false switch.
    """
    sm = get_session_manager()
    session_id = "test-m1-four-asset-bar"
    st = sm.get_or_create(session_id, persona="CMD", language="en")
    asset_rows = [
        {"asset": "Mumbai High", "revenue_cr": 48210.0},
        {"asset": "Neelam Heera", "revenue_cr": 18420.0},
        {"asset": "Bassein & Satellite", "revenue_cr": 22150.0},
        {"asset": "Mehsana", "revenue_cr": 6420.0},
    ]
    bar_vis = {
        "type": "chart",
        "mode": "replace",
        "title": "FY26 Revenue by Asset",
        "chart": {
            "kind": "bar",
            "title": "FY26 Revenue by Asset",
            "x": "asset",
            "y": "revenue_cr",
            "data": asset_rows,
        },
        "table": {"columns": ["asset", "revenue_cr"], "rows": asset_rows},
    }
    st.record_turn(
        {
            "turn_id": "turn-001",
            "language": "en",
            "persona": "CMD",
            "spoken_summary": "Here is FY26 revenue across the top 4 assets.",
            "display_text": "Here is FY26 revenue across the top 4 assets.",
            "visual": bar_vis,
            "insights": ["Mumbai High leads at ₹48,210 Cr"],
            "sources": [{"kind": "data", "object": "hrfin_gold"}],
            "suggestions": [],
            "access": {"status": "allowed"},
            "export_options": ["pdf"],
            "status_events": [],
        },
        user_query="Show FY26 revenue by asset",
        all_rows=asset_rows,
    )

    runner = AgentTurnRunner.__new__(AgentTurnRunner)
    runner.session_manager = sm

    # (a) "Show this as a waterfall" on an untyped 4-asset bar chart must refuse honestly (no unsigned waterfall)
    replot_res = asyncio.run(
        runner._execute_turn_inner(
            query="Show this as a waterfall",
            session_id=session_id,
            persona="CMD",
            language="en",
        )
    )
    assert not FALSE_SUCCESS_RE.search(replot_res["spoken_summary"])
    assert "ui_action" not in replot_res
    assert replot_res["visual"]["chart"]["kind"] == "bar"

    # (b) "Show the Ankleshwar total revenue as a waterfall chart" with a 4-asset bar chart on screen
    # must NOT enter set_chart_kind and re-plot the 4-asset rows; it must proceed to the planner pipeline.
    routed_to_planner: List[str] = []

    async def _fake_planner_turn(query: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        routed_to_planner.append(query)
        b_err = single_value_error()
        return {
            "contract": {
                "turn_id": "turn-002",
                "language": "en",
                "persona": "CMD",
                "spoken_summary": b_err.message("en"),
                "display_text": b_err.message("en"),
                "visual": {
                    "type": "kpi",
                    "mode": "replace",
                    "title": "Ankleshwar Asset: FY26 Gross Revenue",
                    "kpis": [{"label": "Gross Revenue (FY26)", "value": 3098.48, "unit": "₹ crore"}],
                },
                "insights": ["Ankleshwar FY26 revenue: ₹3,098.48 Cr"],
                "sources": [{"kind": "data", "object": "hrfin_gold"}],
                "suggestions": [],
                "access": {"status": "allowed"},
                "export_options": ["pdf"],
                "status_events": ["Planner handled new data question"],
            },
            "meta": None,
        }

    monkeypatch.setattr("app.turn_runner.planner_enabled", lambda: True)
    monkeypatch.setattr("app.turn_runner.run_planner_turn", _fake_planner_turn)

    new_q_res = asyncio.run(
        runner._execute_turn_inner(
            query="Show the Ankleshwar total revenue as a waterfall chart",
            session_id=session_id,
            persona="CMD",
            language="en",
        )
    )
    assert len(routed_to_planner) == 1, "New data question must be routed to the planner, not hijacked by set_chart_kind"
    assert "ui_action" not in new_q_res
    assert not FALSE_SUCCESS_RE.search(new_q_res["spoken_summary"])


def test_m2_multi_period_statement_and_multi_fy_pnl_which_year_and_selected_period() -> None:
    """M2 (BEH-04.12): Multi-period statement or multi-FY P&L trend asks 'Which year?' with FY chips
    when no year is specified, bridges the exact requested FY when specified, and never builds an
    unsigned waterfall from wide multi-year rows.
    """
    sm = get_session_manager()
    pnl_fx = _load_pnl_fixture()
    runner = AgentTurnRunner.__new__(AgentTurnRunner)
    runner.session_manager = sm

    # (a) Multi-period statement visual (FY26..FY22) -> "Show this as a waterfall" -> asks "Which year?"
    st_multi = sm.get_or_create("test-m2-multi-period-stmt", persona="CMD", language="en")
    st_multi.record_turn(
        {
            "turn_id": "turn-001",
            "language": "en",
            "persona": "CMD",
            "spoken_summary": "5-year P&L statement is on screen.",
            "display_text": "5-year P&L statement is on screen.",
            "visual": {
                "type": "statement",
                "mode": "replace",
                "title": "Statement of Profit and Loss (Standalone) · FY22–FY26",
                "statement": pnl_fx,
            },
            "insights": [],
            "sources": [{"kind": "data", "object": "hrfin_gold"}],
            "suggestions": [],
            "access": {"status": "allowed"},
            "export_options": ["pdf"],
            "status_events": [],
        },
        user_query="Show the income statement for FY22 to FY26",
    )

    res_which = asyncio.run(
        runner._execute_turn_inner(
            query="Show this as a waterfall",
            session_id="test-m2-multi-period-stmt",
            persona="CMD",
            language="en",
        )
    )
    assert "which year" in res_which["spoken_summary"].lower()
    assert "ui_action" not in res_which
    assert res_which["visual"]["type"] == "statement"
    assert any("FY26" in s for s in res_which.get("suggestions", []))
    assert any("FY24" in s for s in res_which.get("suggestions", []))

    # (b) Explicit period selection ("Show FY24 as a waterfall") bridges FY24 specifically (PAT = ₹40,525.96 cr)
    res_fy24 = asyncio.run(
        runner._execute_turn_inner(
            query="Show FY24 as a waterfall",
            session_id="test-m2-multi-period-stmt",
            persona="CMD",
            language="en",
        )
    )
    assert res_fy24["visual"]["type"] == "chart"
    chart_fy24 = res_fy24["visual"]["chart"]
    assert chart_fy24["kind"] == "waterfall"
    assert chart_fy24["title"] == "FY24: ₹138,402 cr revenue to ₹40,526 cr PAT"
    assert abs(chart_fy24["data"][-1]["amount_cr"] - 40525.96) <= 0.5

    # (c) Wide multi-year P&L trend table (no line_code) -> "Show this as a waterfall" -> asks "Which year?"
    st_wide = sm.get_or_create("test-m2-wide-pnl-trend", persona="CMD", language="en")
    wide_rows = [
        {"fiscal_year": "FY26", "revenue_from_ops_cr": 132508.14, "ebitda_cr": 62140.0, "pbt_cr": 43247.02, "pat_cr": 32894.02},
        {"fiscal_year": "FY25", "revenue_from_ops_cr": 137846.29, "ebitda_cr": 66740.0, "pbt_cr": 46760.0, "pat_cr": 35610.32},
        {"fiscal_year": "FY24", "revenue_from_ops_cr": 138402.13, "ebitda_cr": 70248.0, "pbt_cr": 53658.0, "pat_cr": 40525.96},
    ]
    wide_cols = list(wide_rows[0].keys())
    st_wide.record_turn(
        {
            "turn_id": "turn-001",
            "language": "en",
            "persona": "CMD",
            "spoken_summary": "Here is the 3-year P&L trend.",
            "display_text": "Here is the 3-year P&L trend.",
            "visual": {
                "type": "table",
                "mode": "replace",
                "title": "P&L Multi-Year Summary",
                "table": {"columns": wide_cols, "rows": wide_rows},
            },
            "insights": [],
            "sources": [{"kind": "data", "object": "hrfin_gold"}],
            "suggestions": [],
            "access": {"status": "allowed"},
            "export_options": ["pdf"],
            "status_events": [],
        },
        user_query="Show multi-year P&L trend",
        all_rows=wide_rows,
    )
    res_wide = asyncio.run(
        runner._execute_turn_inner(
            query="Show this as a waterfall",
            session_id="test-m2-wide-pnl-trend",
            persona="CMD",
            language="en",
        )
    )
    assert "which year" in res_wide["spoken_summary"].lower()
    assert not FALSE_SUCCESS_RE.search(res_wide["spoken_summary"])
    assert "ui_action" not in res_wide
    assert res_wide["visual"]["type"] == "table"


def test_m3_presenter_bridge_error_keeps_table_and_emits_honest_note() -> None:
    """M3: When statement lines fail reconciliation (e.g. subtotal mismatch), build_visual(chart_kind='waterfall')
    must keep vis['type'] == 'table', leave vis['chart'] unset, and attach the BridgeError copy in vis['note'].
    """
    from app.brain.compiler import get_compiler

    corrupt_fx = json.loads((BRIDGE_FIXTURES_DIR / "error_subtotal_mismatch.json").read_text(encoding="utf-8"))
    corrupt_fy = str((corrupt_fx.get("periods") or ["FY26"])[0])
    corrupt_rows = [
        {
            "line_code": r["line_code"],
            "line_item": r["label"],
            "note_ref": "",
            "amount_cr": r["values"][corrupt_fy],
            "prior_fy_cr": None,
            "yoy_delta_cr": None,
            "yoy_change_pct": None,
            "pct_of_revenue": None,
        }
        for r in _rows_of(corrupt_fx)
    ]
    cols = list(corrupt_rows[0].keys())
    spec = QuerySpec(domain="finance", metric="pnl_statement", dimensions=["line_item"], period=Period(fy=corrupt_fy))
    compiled = get_compiler().compile(spec)

    for requested_kind in ("waterfall", "bar"):
        vis = build_visual(
            spec=spec,
            compiled=compiled,
            columns=cols,
            rows=corrupt_rows,
            chart_kind=requested_kind,
            title="ONGC Statement of Profit & Loss · FY25",
            subtitle="FY25",
            mode="replace",
        )
        assert vis["type"] == "table", f"Expected table fallback on BridgeError for {requested_kind}, got {vis['type']}"
        assert "chart" not in vis, "vis['chart'] must be unset on BridgeError"
        assert vis.get("bridge_error", {}).get("code") == "subtotal_mismatch"
        assert "can't build a reliable bridge" in str(vis.get("note") or "").lower()


def test_s4_cash_flow_statement_replot_as_waterfall_preserves_typed_cf_bridge() -> None:
    """S4: Re-plotting a Cash Flow statement (which has line_code in table.columns and a typed CF waterfall
    in vis['chart']) as a waterfall must display the typed CF waterfall, not fail with missing_start.
    """
    from app.brain.compiler import get_compiler

    cf_rows = [
        {"line_code": "pbt_inr_cr", "line_item": "Profit Before Tax", "note_ref": "Ind-AS 7", "section": "Operating", "amount_cr": 43247.02, "prior_fy_cr": 46760.0, "yoy_delta_cr": -3512.98, "pct_of_ocf": 72.3},
        {"line_code": "non_cash_adjustments_cf_inr_cr", "line_item": "Non-Cash Adjustments", "note_ref": "Ind-AS 7", "section": "Operating", "amount_cr": 27352.98, "prior_fy_cr": 28140.0, "yoy_delta_cr": -787.02, "pct_of_ocf": 45.7},
        {"line_code": "working_capital_change_cf_inr_cr", "line_item": "Working Capital Changes", "note_ref": "Ind-AS 7", "section": "Operating", "amount_cr": -940.0, "prior_fy_cr": -1240.0, "yoy_delta_cr": 300.0, "pct_of_ocf": -1.6},
        {"line_code": "income_tax_paid_cf_inr_cr", "line_item": "Income Taxes Paid", "note_ref": "Note 37", "section": "Operating", "amount_cr": 9820.0, "prior_fy_cr": 10480.0, "yoy_delta_cr": -660.0, "pct_of_ocf": 16.4},
        {"line_code": "operating_cash_flow_inr_cr", "line_item": "Operating Cash Flow", "note_ref": "Ind-AS 7", "section": "Subtotal", "amount_cr": 59840.0, "prior_fy_cr": 63180.0, "yoy_delta_cr": -3340.0, "pct_of_ocf": 100.0},
        {"line_code": "investing_cash_flow_inr_cr", "line_item": "Investing Cash Flow", "note_ref": "Ind-AS 7", "section": "Subtotal", "amount_cr": -35188.0, "prior_fy_cr": -51917.0, "yoy_delta_cr": 16729.0, "pct_of_ocf": -58.8},
        {"line_code": "financing_cash_flow_inr_cr", "line_item": "Financing Cash Flow", "note_ref": "Ind-AS 7", "section": "Subtotal", "amount_cr": -21612.0, "prior_fy_cr": -19183.0, "yoy_delta_cr": -2429.0, "pct_of_ocf": -36.1},
        {"line_code": "net_cash_change_inr_cr", "line_item": "Net Cash Change", "note_ref": "Ind-AS 7", "section": "Subtotal", "amount_cr": 3040.0, "prior_fy_cr": -7920.0, "yoy_delta_cr": 10960.0, "pct_of_ocf": 5.1},
    ]
    spec = QuerySpec(domain="finance", metric="cash_flow_statement", dimensions=["line_item"], period=Period(fy="FY26"))
    compiled = get_compiler().compile(spec)
    vis = build_visual(
        spec=spec,
        compiled=compiled,
        columns=list(cf_rows[0].keys()),
        rows=cf_rows,
        chart_kind=None,
        title="ONGC Cash Flow Statement · FY26",
        subtitle="FY26",
        mode="replace",
    )
    assert vis["type"] == "table"

    sm = get_session_manager()
    st = sm.get_or_create("test-s4-cf-waterfall", persona="CMD", language="en")
    st.record_turn(
        {
            "turn_id": "turn-001",
            "language": "en",
            "persona": "CMD",
            "spoken_summary": "FY26 Cash Flow Statement is on screen.",
            "display_text": "FY26 Cash Flow Statement is on screen.",
            "visual": vis,
            "insights": [],
            "sources": [{"kind": "data", "object": "hrfin_gold"}],
            "suggestions": [],
            "access": {"status": "allowed"},
            "export_options": ["pdf"],
            "status_events": [],
        },
        user_query="Show FY26 cash flow statement",
        all_rows=cf_rows,
    )
    runner = AgentTurnRunner.__new__(AgentTurnRunner)
    runner.session_manager = sm
    res = asyncio.run(
        runner._execute_turn_inner(
            query="Show this as a waterfall chart",
            session_id="test-s4-cf-waterfall",
            persona="CMD",
            language="en",
        )
    )
    assert res["visual"]["type"] == "chart"
    assert res["visual"]["chart"]["kind"] == "waterfall"
    assert len(res["visual"]["chart"]["data"]) == 7


def test_r2_m1_which_year_chip_roundtrip_and_s1_s2_s4(monkeypatch: pytest.MonkeyPatch) -> None:
    """R2-M1: Multi-year P&L trend -> 'Show this as a waterfall' -> 'Which year?' chips -> clicking
    'Show FY23 P&L as a waterfall' or 'Show FY23 as a waterfall' routes to the planner/presenter
    single-FY bridge and returns a typed FY23 waterfall (never a second 'Which year?').
    Also verifies R2-S1 (FY in re-plot title/HI copy), R2-S2 (refusal keeps visual.type), and
    R2-S4 (neutral non-bridge copy for non-statement rows).
    """
    monkeypatch.setenv("YUKTI_FORCE_BQ_FAIL", "1")
    sm = get_session_manager()
    runner = AgentTurnRunner.__new__(AgentTurnRunner)
    runner.session_manager = sm

    wide_rows = [
        {"fiscal_year": "FY24", "revenue_from_ops_cr": 138402.13, "ebitda_cr": 70248.0, "pbt_cr": 53658.0, "pat_cr": 40525.96},
        {"fiscal_year": "FY23", "revenue_from_ops_cr": 155517.32, "ebitda_cr": 65120.0, "pbt_cr": 50402.87, "pat_cr": 38828.87},
        {"fiscal_year": "FY22", "revenue_from_ops_cr": 110345.40, "ebitda_cr": 58410.0, "pbt_cr": 46039.74, "pat_cr": 39005.74},
    ]
    wide_cols = list(wide_rows[0].keys())

    for idx, followup_q in enumerate(["Show FY23 P&L as a waterfall", "Show FY23 as a waterfall"]):
        sid = f"test-r2-m1-roundtrip-{idx}"
        st = sm.get_or_create(sid, persona="CMD", language="en")
        st.record_turn(
            {
                "turn_id": "turn-001",
                "language": "en",
                "persona": "CMD",
                "spoken_summary": "3-year P&L line trend is on screen.",
                "display_text": "3-year P&L line trend is on screen.",
                "visual": {
                    "type": "chart",
                    "mode": "replace",
                    "title": "P&L Multi-Year Trend (FY22–FY24)",
                    "chart": {"kind": "line", "data": wide_rows, "x": "fiscal_year", "y": "pat_cr"},
                    "table": {"columns": wide_cols, "rows": wide_rows},
                },
                "insights": [],
                "sources": [{"kind": "data", "object": "hrfin_gold"}],
                "suggestions": [],
                "access": {"status": "allowed"},
                "export_options": ["pdf"],
                "status_events": [],
            },
            user_query="Show P&L trend for FY22 to FY24",
            all_rows=wide_rows,
        )

        # Step 1: "Show this as a waterfall" -> asks "Which year?", keeps visual.type == "chart" (R2-S2)
        res_which = asyncio.run(
            runner._execute_turn_inner(
                query="Show this as a waterfall",
                session_id=sid,
                persona="CMD",
                language="en",
            )
        )
        assert "which year" in res_which["spoken_summary"].lower()
        assert res_which["visual"]["type"] == "chart", "R2-S2: refusal/clarify must not flip chart -> table"
        assert "Show FY23 P&L as a waterfall" in res_which.get("suggestions", [])

        # Step 2: Send chip text ("Show FY23 P&L as a waterfall") or plain ("Show FY23 as a waterfall")
        res_chip = asyncio.run(
            runner._execute_turn_inner(
                query=followup_q,
                session_id=sid,
                persona="CMD",
                language="en",
            )
        )
        assert "which year" not in res_chip["spoken_summary"].lower(), f"Chip '{followup_q}' looped back to Which year?"
        assert res_chip["visual"]["type"] == "chart"
        wf_chart = res_chip["visual"]["chart"]
        assert wf_chart["kind"] == "waterfall"
        assert wf_chart["title"].startswith("FY23:"), f"Expected FY23 bridge title, got {wf_chart['title']}"
        assert all(r.get("type") in ("total", "delta") for r in wf_chart["data"])

    # R2-S1: Presenter-shaped single-FY P&L rows (no fiscal_year column on rows) recover FY25 from title/KPIs
    pnl_fx = _load_pnl_fixture()
    fy25_presenter_rows = [
        {"line_code": r["line_code"], "line_item": r["label"], "amount_cr": r["values"]["FY25"]}
        for r in _rows_of(pnl_fx)
    ]
    st_s1 = sm.get_or_create("test-r2-s1-presenter-fy", persona="CMD", language="hi")
    st_s1.record_turn(
        {
            "turn_id": "turn-001",
            "language": "hi",
            "persona": "CMD",
            "spoken_summary": "FY25 P&L तालिका स्क्रीन पर है।",
            "display_text": "FY25 P&L तालिका स्क्रीन पर है।",
            "visual": {
                "type": "table",
                "mode": "replace",
                "title": "Statement of Profit and Loss · FY25",
                "table": {"columns": ["line_item", "amount_cr", "line_code"], "rows": fy25_presenter_rows},
            },
            "insights": [],
            "sources": [{"kind": "data", "object": "hrfin_gold"}],
            "suggestions": [],
            "access": {"status": "allowed"},
            "export_options": ["pdf"],
            "status_events": [],
        },
        user_query="FY25 P&L दिखाओ",
        all_rows=fy25_presenter_rows,
    )
    res_s1 = asyncio.run(
        runner._execute_turn_inner(
            query="इसे वॉटरफॉल में दिखाओ",
            session_id="test-r2-s1-presenter-fy",
            persona="CMD",
            language="hi",
        )
    )
    assert res_s1["visual"]["chart"]["title"] == "FY25: ₹137,846 cr revenue to ₹35,610 cr PAT"
    assert "FY25" in res_s1["spoken_summary"] and "current period" not in res_s1["spoken_summary"]

    # R2-S4: Untyped non-statement rows (headcount by region on a bar chart) keep visual.type == "chart" and use neutral copy
    hc_rows = [
        {"region": "Mumbai", "headcount": 6200},
        {"region": "Delhi", "headcount": 2100},
        {"region": "Assam", "headcount": 4300},
    ]
    st_s4 = sm.get_or_create("test-r2-s4-non-bridge", persona="CMD", language="en")
    st_s4.record_turn(
        {
            "turn_id": "turn-001",
            "language": "en",
            "persona": "CMD",
            "spoken_summary": "Headcount by region is on screen.",
            "display_text": "Headcount by region is on screen.",
            "visual": {
                "type": "chart",
                "mode": "replace",
                "title": "Headcount by Region",
                "chart": {"kind": "bar", "data": hc_rows, "x": "region", "y": "headcount"},
                "table": {"columns": ["region", "headcount"], "rows": hc_rows},
            },
            "insights": [],
            "sources": [{"kind": "data", "object": "hrfin_gold"}],
            "suggestions": [],
            "access": {"status": "allowed"},
            "export_options": ["pdf"],
            "status_events": [],
        },
        user_query="Show headcount by region",
        all_rows=hc_rows,
    )
    res_s4 = asyncio.run(
        runner._execute_turn_inner(
            query="Show this as a waterfall",
            session_id="test-r2-s4-non-bridge",
            persona="CMD",
            language="en",
        )
    )
    assert res_s4["visual"]["type"] == "chart"
    assert "start-to-end bridge" in res_s4["spoken_summary"].lower()
    assert "statement table" not in res_s4["spoken_summary"].lower()

