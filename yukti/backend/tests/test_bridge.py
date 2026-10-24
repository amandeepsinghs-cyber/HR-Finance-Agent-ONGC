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
