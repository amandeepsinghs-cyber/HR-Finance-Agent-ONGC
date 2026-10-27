"""26-Oct: oil-price overlay — FY averaging, cache fallback and the `overlay` screen command (no network)."""
from datetime import datetime, timezone

import pytest

from app import ui_control
from app.market import oil_prices as op


def _pts():
    # FY25 = Apr-2024..Mar-2025 at $80, FY26 = Apr-2025..Mar-2026 at $70 (one close per day, 30 per month)
    out = []
    for y, m, price in [(2024, mo, 80.0) for mo in range(4, 13)] + [(2025, mo, 80.0) for mo in range(1, 4)] + \
            [(2025, mo, 70.0) for mo in range(4, 13)] + [(2026, mo, 70.0) for mo in range(1, 4)]:
        for d in range(1, 29):
            out.append((datetime(y, m, d, tzinfo=timezone.utc), price))
    return out


def test_fy_of_indian_fiscal_year():
    assert op._fy_of(datetime(2025, 3, 31, tzinfo=timezone.utc)) == 2025
    assert op._fy_of(datetime(2025, 4, 1, tzinfo=timezone.utc)) == 2026


def test_payload_groups_by_indian_fy():
    h = {dt.strftime("%Y-%m-%d"): c for dt, c in _pts()}
    d = op._payload("brent", h, {"regularMarketPrice": 71.5, "regularMarketChangePercent": -1.2}, len(h), 0, stale=False)
    by = {p["fy"]: p for p in d["fy_series"]}
    assert by["FY25"]["avg"] == 80.0 and by["FY26"]["avg"] == 70.0
    assert d["symbol"] == "BZ=F" and d["unit"] == "$/bbl" and d["live"]["price"] == 71.5


def test_normalize_benchmark():
    assert op.normalize_benchmark("WTI") == "wti"
    assert op.normalize_benchmark("west texas") == "wti"
    assert op.normalize_benchmark(None) == "brent"
    assert op.normalize_benchmark("anything") == "brent"


def test_falls_back_to_saved_history(monkeypatch, tmp_path):
    monkeypatch.setattr(op, "_HIST_DIR", tmp_path)
    op._mem.clear(); op._hist.clear()
    (tmp_path / "wti_daily.json").write_text('{"2026-01-01": 60.0, "2026-01-02": 61.0}')

    def boom(*a, **k):
        raise RuntimeError("yahoo down")

    monkeypatch.setattr(op, "_fetch_range", boom)
    saved = op.get_oil_prices("wti")
    assert saved["stale"] is True and saved["history"]["days"] == 2
    op._mem.clear(); op._hist.clear()
    with pytest.raises(RuntimeError):
        op.get_oil_prices("brent")  # no saved history and no live data
    op._mem.clear(); op._hist.clear()


@pytest.mark.parametrize("value,expected", [("brent", "brent"), ("WTI", "wti"), ("oil", "brent"), ("remove", "off"), ("none", "off")])
def test_overlay_screen_command(value, expected):
    cmd, err = ui_control.validate("overlay", value)
    assert err is None and cmd == {"action": "overlay", "value": expected}
    assert ui_control.to_legacy_ui_action(cmd)["command"] == "overlay"


def test_overlay_rejects_unknown_benchmark():
    cmd, err = ui_control.validate("overlay", "gold")
    assert cmd is None and "Allowed" in err


# ---- direct oil-price questions (26-Oct) ----
from app.market import oil_intent  # noqa: E402


@pytest.mark.parametrize(
    "q,bench,months",
    [
        ("Can you plot? Can you plot the Brent oil price? The past 5 years.", "brent", 60),
        ("Show WTI trend for the last 3 years", "wti", 36),
        ("plot brent for the last 18 months", "brent", 18),
        ("oil price history", "brent", 60),
    ],
)
def test_detect_oil_plot(q, bench, months):
    assert oil_intent.detect_oil_plot(q) == {"benchmark": bench, "months": months}


@pytest.mark.parametrize("q", ["Show revenue with brent", "What if Brent falls to 60 dollars", "overlay brent", "How many executives in Delhi?", "export it as excel"])
def test_detect_oil_plot_leaves_other_questions(q):
    assert oil_intent.detect_oil_plot(q) is None


def test_oil_plot_contract(monkeypatch):
    from datetime import datetime, timedelta, timezone

    today = datetime.now(timezone.utc)
    hist = {(today - timedelta(days=i)).strftime("%Y-%m-%d"): 70.0 + (i % 30) for i in range(1, 2000)}
    payload = {
        "benchmark": "brent", "symbol": "BZ=F", "label": "Brent crude", "short": "Brent", "unit": "$/bbl",
        "live": {"price": 110.0, "change_pct": -1.5, "as_of": today.isoformat()},
        "fy_series": [], "daily": [], "monthly": [], "history": {"saved_days": 1999, "new_days": 2},
        "source": "Yahoo Finance (BZ=F)", "fetched_at": "x", "stale": False,
    }
    monkeypatch.setattr(oil_intent, "get_oil_prices", lambda b: payload)
    monkeypatch.setattr(oil_intent, "get_daily_history", lambda b: hist)
    c = oil_intent.build_oil_plot_contract({"benchmark": "brent", "months": 36}, "CMD", "t1", "en", 0.0)
    v = c["visual"]
    data = v["chart"]["data"]
    assert v["type"] == "chart" and v["chart"]["kind"] == "line" and 1090 <= len(data) <= 1100  # ~3 years of days + today
    assert data[-1] == {"date": "Today (live)", "brent_usd_bbl": 110.0}
    assert v["kpis"][0]["value"] == 110.0 and "$110.00" in c["spoken_summary"]
    assert "1,999 days from saved history + 2 new day(s)" in c["status_events"][0]
    assert c["sources"][0]["kind"] == "data" and "Yahoo" in c["sources"][0]["object"]


def test_incremental_fetch_asks_only_for_missing_days(monkeypatch, tmp_path):
    monkeypatch.setattr(op, "_HIST_DIR", tmp_path)
    op._mem.clear(); op._hist.clear()
    (tmp_path / "brent_daily.json").write_text('{"2026-01-01": 60.0, "2026-01-02": 61.0}')
    calls = []

    def fake(symbol, start):
        calls.append(start)
        return {"2026-01-02": 61.5, "2026-01-05": 62.0}, {"regularMarketPrice": 62.3}

    monkeypatch.setattr(op, "_fetch_range", fake)
    d = op.get_oil_prices("brent")
    assert calls[0] is not None and calls[0].strftime("%Y-%m-%d") == "2025-12-28"  # last saved day minus 5-day overlap
    assert d["history"]["saved_days"] == 2 and d["history"]["new_days"] == 1 and d["history"]["days"] == 3
    assert op.get_daily_history("brent")["2026-01-02"] == 61.5  # late correction overwrote the saved close
    op._mem.clear(); op._hist.clear()


# ---- 27-Oct: rupee + revenue drivers / portfolio mix ----
from app.market import revenue_drivers as rd  # noqa: E402


def test_rupee_benchmark_and_overlay():
    assert op.normalize_benchmark("rupee") == "inr" and op.BENCHMARKS["inr"]["symbol"] == "INR=X"
    cmd, err = ui_control.validate("overlay", "rupee")
    assert err is None and cmd["value"] == "inr"
    assert oil_intent.detect_oil_plot("plot the rupee against the dollar for the past 5 years") == {"benchmark": "inr", "months": 60}


@pytest.mark.parametrize("q", [
    "I see that the oil price is decreasing, even then the revenue is not decreasing. Why not?",
    "Why did revenue hold up while oil prices fell?",
    "Explain why ONGC revenue didn't fall despite lower Brent",
])
def test_detect_revenue_drivers(q):
    assert rd.detect_revenue_drivers(q) == {"kind": "drivers", "years": 5}


@pytest.mark.parametrize("q", [
    "So can you draw that portfolio for the past five years, how it has changed?",
    "How has the revenue mix changed over the last 4 years?",
])
def test_detect_portfolio_mix(q):
    assert rd.detect_portfolio_mix(q)["kind"] == "mix"


@pytest.mark.parametrize("q", ["Show revenue for the last 10 years", "How many executives are in Delhi?", "plot brent for 5 years"])
def test_drivers_and_mix_leave_other_questions(q):
    assert rd.detect_revenue_drivers(q) is None and rd.detect_portfolio_mix(q) is None


def _fin():
    rows = []
    for fy, rev, crude, gas, vap, lev, saed, cmmt, gbcm, pat in [
        ("FY22", 110345, 83661, 12441, 13860, 27932, 103, 20.3, 16.75, 40306),
        ("FY23", 155517, 103008, 37417, 14330, 45284, 11054, 19.19, 16.68, 40097),
        ("FY26", 132508, 83810, 36330, 11879, 26148, 63, 18.79, 15.49, 32894),
    ]:
        rows.append(dict(fiscal_year=fy, revenue_cr=rev, crude_cr=crude, gas_cr=gas, vap_cr=vap, levies_cr=lev, saed_cr=saed,
                         crude_mmt=cmmt, gas_bcm=gbcm, pat_cr=pat))
    return rows


def test_drivers_contract_math(monkeypatch):
    monkeypatch.setattr(rd, "_financials", _fin)
    fx = {"brent": {"FY22": 79.92, "FY23": 94.99, "FY26": 69.04}, "inr": {"FY22": 74.51, "FY23": 80.32, "FY26": 88.37}}
    monkeypatch.setattr(rd, "get_oil_prices", lambda b: {"fy_series": [{"fy": k, "avg": v, "provisional": False} for k, v in fx[b].items()]})
    c = rd.build_drivers_contract({"years": 5}, "CMD", "t", "en", 0.0)
    assert "From FY23 to FY26, Brent fell 27% in dollars" in c["spoken_summary"]
    assert "revenue fell only 15%" in c["spoken_summary"] and "rupee weakened 10%" in c["spoken_summary"]
    data = c["visual"]["chart"]["data"]
    assert data[0]["ongc_revenue"] == 100.0 and data[-1]["rupees_per_dollar"] == round(88.37 / 74.51 * 100, 1)
    assert any("₹11,054 cr in FY23 vs ₹63 cr in FY26" in i for i in c["insights"])
    m = rd.build_mix_contract({"years": 5}, "CMD", "t", "en", 0.0)
    assert m["visual"]["chart"]["kind"] == "stacked_bar" and "natural gas grew from 11% to 27%" in m["spoken_summary"]


def test_indian_grouping():
    assert rd._cr(155517) == "₹1,55,517 cr" and rd._cr(-19198) == "-₹19,198 cr" and rd._cr(63) == "₹63 cr"


# ---- 27-Oct: DCF follow-ups ----
from types import SimpleNamespace  # noqa: E402

from app.finance.dcf import followup as fu  # noqa: E402

_VIS = {
    "type": "dcf_model",
    "per_share": {"intrinsic_inr": 233.24, "market_inr": 284.65, "upside_pct": -18.06, "verdict": "overvalued", "market_date": "2026-03-30"},
    "assumptions": {"wacc_pct": {"value": 11.6556}, "terminal_g_pct": {"value": 3.0}, "brent_usd": {"value": 80.0}, "capex_scale_pct": {"value": 100.0},
                    "production_decline_pct": {"value": 0.0}, "fx_inr_usd": {"value": 83.0}, "exit_ev_ebitda": {"value": 4.5}},
    "wacc_build": {"wacc_pct": 11.6556, "ke_pct": 12.4605, "rf_used_pct": 7.0782, "beta_adj": 0.8397, "erp_total_pct": 7.0754,
                   "kd_after_tax_pct": 3.0884, "weight_equity": 0.914, "weight_debt": 0.086},
    "terminal": {"tv_inr_cr": 196663.6, "pv_tv_inr_cr": 65300.9, "tv_exit_inr_cr": 332539.0, "implied_g_pct": 6.37, "warning": True},
    "bridge": [{"label": "PV of FCFF", "value_inr_cr": 133534.2}, {"label": "PV of TV", "value_inr_cr": 65300.9},
               {"label": "Enterprise Value (EV)", "value_inr_cr": 198835.1}, {"label": "Add: Listed Inv", "value_inr_cr": 113378.6},
               {"label": "Equity Value", "value_inr_cr": 293427.9}],
    "tornado": {"bars": [{"driver": "prod", "low_inr": 684.76, "high_inr": 16.91}, {"driver": "brent", "low_inr": 170.1, "high_inr": 296.38},
                         {"driver": "capex", "low_inr": 294.76, "high_inr": 171.73}, {"driver": "wacc", "low_inr": 249.68, "high_inr": 220.01}]},
    "forecast": {"years": ["FY27", "FY36"], "lines": {"fcff": [27377.7, 30000.0], "pv_fcff": [24519.8, 10000.0]}},
}


def _sess(latest=True):
    turns = [{"visual": _VIS}] + ([] if latest else [{"visual": {"type": "chart"}}])
    return SimpleNamespace(turns=turns, last_agent_result={"agent": "dcf_agent", "inputs": {}}, pending_actions={})


@pytest.mark.parametrize("q,intent,extra", [
    ("What are the drivers of the valuation?", "drivers", None),
    ("Why is ONGC overvalued?", "explain", "bridge"),
    ("How much of the value comes from terminal value?", "explain", "terminal"),
    ("What is the WACC made of?", "explain", "wacc"),
    ("what if WACC is 12%", "whatif", {"wacc_pct": 12.0}),
    ("What if Brent is $60?", "whatif", {"brent_usd": 60.0}),
    ("capex up 20%", "whatif", {"capex_scale_pct": 120.0}),
    ("WACC 1 point higher", "whatif", {"wacc_pct": 12.6556}),
    ("why?", "explain", "summary"),
])
def test_detect_dcf_followup(q, intent, extra):
    d = fu.detect_dcf_followup(q, _sess())
    assert d and d["intent"] == intent
    if isinstance(extra, dict):
        assert d["overrides"] == extra
    elif extra:
        assert d["topic"] == extra


def test_dcf_followup_needs_a_dcf_and_leaves_other_topics():
    assert fu.detect_dcf_followup("What drives the valuation?", SimpleNamespace(turns=[], last_agent_result=None)) is None
    assert fu.detect_dcf_followup("Show headcount in Delhi", _sess()) is None
    assert fu.detect_dcf_followup("why?", _sess(latest=False)) is None  # generic follow-up only when the DCF is the latest card
    assert fu.detect_dcf_followup("Run a new DCF", _sess()) is None


def test_dcf_drivers_answer_uses_engine_numbers():
    c = fu.answer_drivers(fu.facts_from_visual(_VIS), "t", "CMD", "en", 0.0)
    assert c["visual"]["type"] == "tornado" and c["visual"]["tornado"]["bars"][0]["driver"] == "Production trend"
    assert "₹685 to ₹17 per share" in c["spoken_summary"] and "33% of enterprise value" in c["spoken_summary"]


def test_dcf_explain_rejects_invented_numbers(monkeypatch):
    f = fu.facts_from_visual(_VIS)
    assert fu.grounded("Intrinsic value is ₹233 against ₹285, 33% from terminal value.", f)
    assert not fu.grounded("Intrinsic value is ₹412 per share.", f)
    monkeypatch.setattr(fu, "_gemini_explain", lambda q, f: "The fair value is ₹999 per share.")
    c = fu.answer_explain("why overvalued?", f, "bridge", "t", "CMD", "en", 0.0)
    assert "999" not in c["spoken_summary"] and "₹233.24" in c["spoken_summary"]  # deterministic fallback
    assert c["visual"]["chart"]["kind"] == "waterfall"
    assert all(r["step"] not in ("Enterprise Value (EV)", "Equity Value") for r in c["visual"]["chart"]["data"])


def test_dcf_whatif_reruns_engine(monkeypatch):
    calls = {}

    def fake_run(dcf, overrides):
        calls["o"] = overrides
        return {"per_share": {"intrinsic_inr": 107.0}, "bridge": [{"label": "Enterprise Value (EV)", "value_inr_cr": 120000.0}]}

    monkeypatch.setattr(fu, "run_whatif", fake_run)
    d = fu.detect_dcf_followup("What if Brent is $60?", _sess())
    c = fu.answer_dcf_followup(d, "What if Brent is $60?", "CMD", "t", "en", 0.0)
    assert calls["o"] == {"brent_usd": 60.0}
    assert "from ₹233 to ₹107 per share" in c["spoken_summary"] and c["visual"]["type"] == "kpi"


def test_whatif_rejects_growth_above_wacc():
    assert "terminal_g_pct" not in fu.parse_whatif("what if wacc is 6% and terminal growth is 5.5%", _VIS)


def test_generic_followup_after_a_dcf_followup_card():
    s = _sess()
    s.turns.append({"visual": {"type": "chart"}, "sources": [{"kind": "data", "object": "DCF engine (this conversation's run)"}]})
    d = fu.detect_dcf_followup("why?", s)
    assert d and d["intent"] == "explain"
