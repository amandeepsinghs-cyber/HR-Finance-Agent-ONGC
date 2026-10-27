"""DCF follow-up questions (27-Oct): answers questions about the DCF valuation already run in this conversation.

Before this, a follow-up such as "what drives the valuation?" went to the data planner, which only knows ONGC's
tables, so Yukti could not answer. The DCF result (per-share value, WACC build, EV→equity bridge, terminal value,
forecast, sensitivity grid and tornado) is in the session; this module reads it back.

Intents
  drivers  "what drives the valuation / which assumptions matter most"  → tornado chart + deterministic narrative
  explain  "why overvalued / how much is terminal value / what is the WACC made of / explain the cash flows"
           → a topic visual (bridge waterfall, WACC table, terminal KPIs, FCFF chart) + an explanation written by
             Gemini from the model's numbers only; any number not in the model rejects the text (deterministic fallback)
  whatif   "what if WACC is 12% / g 2% / Brent $60 / capex +20% / rupee 90" → re-runs the DCF engine with the change
           (same input builder and validation as the original run) and compares base vs scenario
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("yukti.dcf.followup")

DRIVER_LABELS: Dict[str, Tuple[str, str, str]] = {
    # engine id: (label, low case, high case) — the engine's tornado mutators (app/finance/dcf/sensitivity.py)
    "prod": ("Production trend", "output rising 3%/yr", "output falling 3%/yr"),
    "brent": ("Brent price", "−$10/bbl", "+$10/bbl"),
    "capex": ("Capex level", "−20% of plan", "+20% of plan"),
    "opex": ("Operating cost per boe", "−15%", "+15%"),
    "fx": ("Rupee per dollar", "−5% (stronger ₹)", "+5% (weaker ₹)"),
    "wacc": ("WACC (discount rate)", "−1 pt", "+1 pt"),
    "holdco": ("Holding-company discount", "0%", "30%"),
    "g": ("Terminal growth", "−1 pt", "+1 pt"),
}

_DCF_WORDS = re.compile(
    r"\b(dcf|valuation|valued?|value per share|intrinsic|fair value|under ?valued|over ?valued|upside|downside|"
    r"wacc|cost of capital|cost of equity|beta|discount rate|discounting|terminal|tv|gordon|exit multiple|"
    r"fcff|free cash flow|cash flows?|forecast|bridge|enterprise value|equity value|\bev\b|investments|"
    r"assumptions?|drivers?|sensitiv\w*|tornado|per share|market price|share price|target price)\b",
    re.I,
)
_DRIVERS = re.compile(r"\b(drivers?|drive|driving|sensitiv\w*|matters? most|most important|key assumptions?|what moves|levers?|tornado|swing)\b", re.I)
_WHATIF = re.compile(r"\b(what if|what happens if|if (the )?(wacc|discount|terminal|growth|brent|oil|crude|capex|production|rupee|holdco|fx)|assume|assuming|suppose|scenario|change (the )?|with (a |an )?(wacc|terminal|brent|capex)|instead of|increase|decrease|raise|lower|cut)\b", re.I)
_GENERIC_FOLLOWUP = re.compile(r"^\s*(why|how|explain|what does (this|that|it) mean|tell me more|elaborate|and why|so why|is that (good|bad|right)|really)\b", re.I)
_NEW_TOPIC = re.compile(r"\b(employees?|headcount|delhi|transfer|leave|salary|payroll|policy|roster|p&l statement|balance sheet|mou|field|asset|plot|chart of|export|download)\b", re.I)

# what-if inputs: name → (regex for the subject, valid range, unit word)
_WI_FIELDS: Dict[str, Tuple[str, Tuple[float, float]]] = {
    "wacc_pct": (r"wacc|discount rate|cost of capital", (5.0, 20.0)),
    "terminal_g_pct": (r"terminal (growth|g)|long[- ]term growth|perpetual growth|\bg\b|growth rate", (0.0, 6.0)),
    "brent_usd": (r"brent|oil price|crude price|crude|oil", (30.0, 160.0)),
    "capex_scale_pct": (r"capex|capital expenditure", (40.0, 160.0)),
    "production_decline_pct": (r"production decline|decline rate|production", (-10.0, 25.0)),
    "holdco_discount_pct": (r"holdco|holding[- ]company discount|conglomerate discount", (0.0, 60.0)),
    "fx_inr_usd": (r"rupee|exchange rate|usd ?inr|inr|fx|dollar", (60.0, 130.0)),
}


# ---------------------------------------------------------------------------------------------------------- session

def find_last_dcf(session_state: Any, max_back: int = 12) -> Optional[Dict[str, Any]]:
    """Latest DCF visual in this conversation (within the last `max_back` turns), plus whether it is the latest card."""
    turns = list(getattr(session_state, "turns", []) or [])

    def is_dcf_card(t: Dict[str, Any]) -> bool:
        vis = (t or {}).get("visual") or {}
        if isinstance(vis, dict) and vis.get("type") == "dcf_model":
            return True
        src = ((t or {}).get("sources") or [{}])[0] if (t or {}).get("sources") else {}
        return str((src or {}).get("object", "")).startswith("DCF engine")  # a DCF follow-up answer

    latest_is_dcf = bool(turns) and is_dcf_card(turns[-1])
    for i, t in enumerate(reversed(turns[-max_back:])):
        vis = (t or {}).get("visual") or {}
        if isinstance(vis, dict) and vis.get("type") == "dcf_model" and vis.get("per_share"):
            inputs = {}
            lar = getattr(session_state, "last_agent_result", None) or {}
            if lar.get("agent") == "dcf_agent":
                inputs = dict(lar.get("inputs") or {})
            return {"visual": vis, "is_latest": latest_is_dcf, "inputs": inputs}
    return None


def detect_dcf_followup(query: str, session_state: Any) -> Optional[Dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return None
    dcf = find_last_dcf(session_state)
    if not dcf:
        return None
    if re.search(r"\b(run|re-?run|build|create|do|start)\b.{0,20}\b(dcf|valuation)\b", q, re.I) and not _WHATIF.search(q):
        return None  # a new DCF request goes to the normal DCF agent flow
    overrides = parse_whatif(q, dcf["visual"])
    if overrides and (_WHATIF.search(q) or re.search(r"\b(at|to|of|is|by)\s*[$₹]?\s*\d", q) or re.search(r"\b(up|down|higher|lower)\b", q, re.I)):
        return {"intent": "whatif", "overrides": overrides, "dcf": dcf}
    on_topic = bool(_DCF_WORDS.search(q))
    if not on_topic:
        if not (dcf["is_latest"] and _GENERIC_FOLLOWUP.search(q) and not _NEW_TOPIC.search(q)):
            return None
    if _DRIVERS.search(q):
        return {"intent": "drivers", "dcf": dcf}
    return {"intent": "explain", "dcf": dcf, "topic": _topic(q)}


def _topic(q: str) -> str:
    if re.search(r"\b(wacc|cost of capital|cost of equity|beta|discount rate|risk[- ]free|erp|equity risk)\b", q, re.I):
        return "wacc"
    if re.search(r"\b(terminal|tv|gordon|exit multiple|perpetuity)\b", q, re.I):
        return "terminal"
    if re.search(r"\b(fcff|free cash flow|cash flows?|forecast|projection|revenue forecast|ebit)\b", q, re.I):
        return "forecast"
    if re.search(r"\b(bridge|enterprise value|equity value|\bev\b|debt|investments|cash|over ?valued|under ?valued|why .*(value|price)|upside|downside|market price|share price|gap)\b", q, re.I):
        return "bridge"
    return "summary"


def _base_value(vis: Dict[str, Any], field: str) -> Optional[float]:
    a = (vis.get("assumptions") or {}).get(field)
    if isinstance(a, dict):
        a = a.get("value")
    try:
        return float(a)
    except (TypeError, ValueError):
        return None


def parse_whatif(q: str, vis: Dict[str, Any]) -> Dict[str, float]:
    """Absolute ('WACC 12%', 'Brent at $60') or relative ('WACC 1 pt higher', 'capex up 20%') input changes."""
    out: Dict[str, float] = {}
    ql = q.lower()
    for field, (subj, (lo, hi)) in _WI_FIELDS.items():
        m_subj = re.search(subj, ql)
        if not m_subj:
            continue
        tail = ql[m_subj.end(): m_subj.end() + 60]
        head = ql[max(0, m_subj.start() - 40): m_subj.start()]
        base = _base_value(vis, field)
        rel_up = re.search(r"\b(up|higher|increase[sd]?|raise[sd]?|rise[sn]?|more)\b", tail + " " + head)
        rel_dn = re.search(r"\b(down|lower|decrease[sd]?|cut|reduce[sd]?|fall[sn]?|drops?|less)\b", tail + " " + head)
        m_by = re.search(r"\bby\s*[$₹]?\s*(-?\d+(?:\.\d+)?)", tail)
        m_num = re.search(r"[$₹]?\s*(-?\d+(?:\.\d+)?)\s*(%|pct|percent|pts?|points?|bps|dollars?|usd|/bbl|a barrel)?", tail)
        if not m_num:
            continue
        val = float((m_by or m_num).group(1))
        unit = (m_num.group(2) or "").strip()
        if "bps" in unit:
            val = val / 100.0
        sign = -1.0 if (rel_dn and not rel_up) else 1.0
        relative = bool(m_by) or (
            bool(rel_up or rel_dn)
            and (re.search(r"pts?|points?|bps", unit) or field in ("capex_scale_pct", "brent_usd", "fx_inr_usd"))
        )
        if relative and base is not None:
            val = base + sign * val
        if lo <= val <= hi:
            out[field] = round(val, 4)
    if "terminal_g_pct" in out and "wacc_pct" in out and out["terminal_g_pct"] >= out["wacc_pct"] - 1:
        out.pop("terminal_g_pct")  # invalid combination: Gordon growth needs g well below WACC
    return out


# ---------------------------------------------------------------------------------------------------------- facts

def _f(v: Any, d: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _cr(v: float) -> str:
    n = int(round(abs(v)))
    s = str(n)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts: List[str] = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return f"{'-' if v < 0 else ''}₹{s} cr"


def facts_from_visual(vis: Dict[str, Any]) -> Dict[str, Any]:
    ps = vis.get("per_share") or {}
    wb = vis.get("wacc_build") or {}
    term = vis.get("terminal") or {}
    bridge = {b.get("label"): _f(b.get("value_inr_cr")) for b in (vis.get("bridge") or []) if isinstance(b, dict)}
    ev = bridge.get("Enterprise Value (EV)") or (bridge.get("PV of FCFF", 0) + bridge.get("PV of TV", 0))
    eq = bridge.get("Equity Value", 0.0)
    pv_tv = bridge.get("PV of TV", _f(term.get("pv_tv_inr_cr")))
    pv_fcff = bridge.get("PV of FCFF", 0.0)
    listed = bridge.get("Add: Listed Inv", 0.0)
    a = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in (vis.get("assumptions") or {}).items()}
    tornado_raw = (vis.get("tornado") or {}).get("bars") if isinstance(vis.get("tornado"), dict) else vis.get("tornado")
    bars = []
    for b in tornado_raw or []:
        d = str(b.get("driver"))
        lbl, lo_case, hi_case = DRIVER_LABELS.get(d, (d, "low", "high"))
        lo, hi = _f(b.get("low_inr")), _f(b.get("high_inr"))
        bars.append({"driver": d, "label": lbl, "low_case": lo_case, "high_case": hi_case, "low_inr": round(lo, 2), "high_inr": round(hi, 2), "swing_inr": round(abs(hi - lo), 2)})
    bars.sort(key=lambda b: b["swing_inr"], reverse=True)
    fc = vis.get("forecast") or {}
    years = fc.get("years") or []
    lines = fc.get("lines") or {}
    return {
        "intrinsic_inr": round(_f(ps.get("intrinsic_inr")), 2),
        "market_inr": round(_f(ps.get("market_inr")), 2),
        "market_date": ps.get("market_date"),
        "upside_pct": round(_f(ps.get("upside_pct")), 1),
        "verdict": ps.get("verdict"),
        "ev_cr": round(ev), "equity_cr": round(eq), "pv_fcff_cr": round(pv_fcff), "pv_tv_cr": round(pv_tv),
        "tv_share_of_ev_pct": round(pv_tv / ev * 100, 1) if ev else None,
        "listed_investments_cr": round(listed),
        "investments_share_of_equity_pct": round(listed / eq * 100, 1) if eq else None,
        "bridge": [{"label": k, "value_cr": round(v)} for k, v in bridge.items()],
        "wacc": {k: round(_f(v), 4) for k, v in wb.items() if isinstance(v, (int, float))},
        "terminal": {"g_pct": a.get("terminal_g_pct"), "tv_cr": round(_f(term.get("tv_inr_cr"))), "pv_tv_cr": round(_f(term.get("pv_tv_inr_cr"))),
                     "exit_multiple": a.get("exit_ev_ebitda"), "tv_exit_cr": round(_f(term.get("tv_exit_inr_cr"))),
                     "implied_g_from_exit_pct": round(_f(term.get("implied_g_pct")), 2), "methods_diverge": bool(term.get("warning"))},
        "assumptions": {k: a.get(k) for k in ("wacc_pct", "terminal_g_pct", "brent_usd", "fx_inr_usd", "gas_price_usd_mmbtu", "capex_scale_pct",
                                               "production_decline_pct", "opex_per_boe", "effective_levy_rate", "tax_rate_pct", "holdco_discount_pct",
                                               "vol_crude_mmt", "vol_gas_bcm", "shares_outstanding") if k in a},
        "drivers": bars,
        "forecast": {"years": years, "fcff_cr": lines.get("fcff"), "pv_fcff_cr": lines.get("pv_fcff"), "revenue_cr": lines.get("revenue")},
        "disclaimer": vis.get("disclaimer") or "Illustrative valuation, not investment advice.",
    }


# ---------------------------------------------------------------------------------------------------------- answers

def _base_contract(turn_id: str, persona: str, language: str, t0: float, spoken: str, visual: Dict[str, Any],
                   insights: List[str], suggestions: List[str], status: str) -> Dict[str, Any]:
    return {
        "turn_id": turn_id,
        "language": language,
        "persona": persona,
        "spoken_summary": spoken,
        "display_text": spoken,
        "visual": visual,
        "insights": insights,
        "insights_v2": [{"kind": k, "text": t} for k, t in zip(["headline", "trend", "comparison", "note", "risk"], insights)],
        "context_chips": [{"label": persona, "kind": "role"}, {"label": "DCF follow-up", "kind": "subject"}],
        "sources": [{"kind": "data", "object": "DCF engine (this conversation's run)", "sql": "per-share value, WACC build, bridge, terminal value, sensitivity"}],
        "suggestions": suggestions,
        "access": {"status": "allowed"},
        "export_options": ["xlsx", "pdf"],
        "status_events": [status],
        "caveat": "Illustrative valuation, not investment advice.",
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def answer_drivers(f: Dict[str, Any], turn_id: str, persona: str, language: str, t0: float) -> Dict[str, Any]:
    bars = f["drivers"]
    top = bars[:3]
    iv = f["intrinsic_inr"]
    lines = [f"{b['label']} ({b['low_case']} / {b['high_case']}): ₹{b['low_inr']:.0f} to ₹{b['high_inr']:.0f} per share" for b in top]
    spoken = (
        f"The valuation of ₹{iv:.0f} per share is most sensitive to the {top[0]['label'][0].lower() + top[0]['label'][1:]}, then the {top[1]['label']} and the {top[2]['label'][0].lower() + top[2]['label'][1:]}. "
        f"{lines[0]}. "
        + (f"Terminal value is {f['tv_share_of_ev_pct']:.0f}% of enterprise value, " if f.get("tv_share_of_ev_pct") is not None else "")
        + (f"and listed investments (HPCL, OVL stakes and others) add {_cr(f['listed_investments_cr'])}, {f['investments_share_of_equity_pct']:.0f}% of equity value." if f.get("investments_share_of_equity_pct") else "")
    )
    insights = [f"#{i + 1} {ln}." for i, ln in enumerate(lines)]
    insights.append(
        f"Operating cash flows are worth {_cr(f['pv_fcff_cr'])} today and the terminal value {_cr(f['pv_tv_cr'])}"
        + (f" ({f['tv_share_of_ev_pct']:.0f}% of EV)" if f.get("tv_share_of_ev_pct") is not None else "") + "."
    )
    if f.get("investments_share_of_equity_pct"):
        insights.append(f"Listed investments add {_cr(f['listed_investments_cr'])} ({f['investments_share_of_equity_pct']:.0f}% of equity value): their market value moves the per-share value too.")
    visual = {
        "type": "tornado",
        "mode": "replace",
        "title": f"What drives the DCF value · base ₹{iv:.2f} per share",
        "tornado": {
            "output": {"name": "Intrinsic value per share", "unit": "INR", "base": iv},
            "bars": [{"driver": b["label"], "low_input": b["low_case"], "high_input": b["high_case"], "low_inr": b["low_inr"], "high_inr": b["high_inr"]} for b in bars],
            "source": "DCF engine sensitivity runs (this conversation)",
        },
    }
    return _base_contract(turn_id, persona, language, t0, spoken, visual, insights[:5],
                          ["What if WACC is 12%?", "How much of the value is terminal value?", "Why is it overvalued vs the market price?"],
                          "Ranked value drivers from the DCF engine's sensitivity runs")


def _topic_visual(f: Dict[str, Any], topic: str) -> Dict[str, Any]:
    if topic == "bridge":
        # steps only: the waterfall computes the running total itself (subtotal rows would be double-counted)
        rows = [{"step": b["label"].replace("Less: ", "− ").replace("Add: ", "+ "), "value_cr": b["value_cr"]}
                for b in f["bridge"] if b["label"] not in ("Enterprise Value (EV)", "Equity Value") and b["value_cr"]]
        return {"type": "chart", "mode": "replace", "title": "From enterprise value to equity value (₹ cr)",
                "table": {"columns": ["step", "value_cr"], "rows": rows, "total_rows": len(rows), "masking": {"level": "none"}},
                "chart": {"kind": "waterfall", "data": rows, "x": "step", "y": "value_cr", "category": "step", "value": "value_cr", "unit": "₹ Cr",
                          "title": "From enterprise value to equity value (₹ cr)"}}
    if topic == "wacc":
        w = f["wacc"]
        names = {"rf_used_pct": "Risk-free rate (%)", "beta_adj": "Beta (adjusted)", "erp_total_pct": "Equity risk premium (%)", "ke_pct": "Cost of equity (%)",
                 "kd_used_pct": "Cost of debt, pre-tax (%)", "kd_after_tax_pct": "Cost of debt, after tax (%)", "tax_rate_pct": "Tax rate (%)",
                 "weight_equity": "Weight of equity", "weight_debt": "Weight of debt", "wacc_pct": "WACC (%)"}
        rows = [{"component": names[k], "value": round(w[k], 4)} for k in names if k in w]
        return {"type": "table", "mode": "replace", "title": "WACC build", "table": {"columns": ["component", "value"], "rows": rows, "total_rows": len(rows), "masking": {"level": "none"}}}
    if topic == "forecast" and f["forecast"].get("years") and f["forecast"].get("fcff_cr"):
        rows = [{"year": y, "fcff_cr": fc, "pv_fcff_cr": pv} for y, fc, pv in zip(f["forecast"]["years"], f["forecast"]["fcff_cr"], f["forecast"]["pv_fcff_cr"] or [])]
        return {"type": "chart", "mode": "replace", "title": "Free cash flow forecast and its present value (₹ cr)",
                "table": {"columns": ["year", "fcff_cr", "pv_fcff_cr"], "rows": rows, "total_rows": len(rows), "masking": {"level": "none"}},
                "chart": {"kind": "grouped_bar", "data": rows, "x": "year", "y": "fcff_cr", "category": "year", "value": "fcff_cr", "unit": "₹ Cr",
                          "title": "Free cash flow forecast and its present value (₹ cr)"}}
    t = f["terminal"]
    return {"type": "kpi", "mode": "replace", "title": "DCF at a glance" if topic != "terminal" else "Terminal value",
            "kpis": ([{"label": "Intrinsic value", "value": f["intrinsic_inr"], "unit": "₹/share"},
                      {"label": "Market price", "value": f["market_inr"], "unit": "₹/share"},
                      {"label": "Upside / downside", "value": f["upside_pct"], "unit": "%"}] if topic != "terminal" else
                     [{"label": "Terminal value (PV)", "value": t["pv_tv_cr"], "unit": "₹ crore"},
                      {"label": "Share of EV", "value": f.get("tv_share_of_ev_pct") or 0, "unit": "%"},
                      {"label": "Terminal growth", "value": _f(t.get("g_pct")), "unit": "%"}])}


_EXPLAIN_SYS = """You are Yukti, explaining a DCF valuation of ONGC to its Chairman. Answer the question in 2-4 short, plain sentences
for a senior executive. Do not greet or address the user by name (this is mid-conversation). Use ₹ (not INR) and Indian
digit grouping (e.g. ₹1,98,835 crore). Use ONLY the numbers in the JSON below (you may round them); do not invent or compute new numbers
beyond simple differences already implied. Explain the "why" in business terms (cash flows, discount rate, terminal value,
investments, debt and provisions, market price). If the JSON cannot answer, say what it does show. Indian English. Plain text."""

_client = None


def _gemini_explain(question: str, f: Dict[str, Any]) -> Optional[str]:
    global _client
    try:
        from google import genai
        from google.genai import types
        from app.config import DEFAULT_TEXT_MODEL, GCP_PROJECT, VERTEX_TEXT_LOCATION

        if _client is None:
            _client = genai.Client(vertexai=True, project=GCP_PROJECT, location=VERTEX_TEXT_LOCATION)
        slim = {k: v for k, v in f.items() if k != "forecast"}
        slim["forecast_first_last"] = {
            "years": (f["forecast"].get("years") or [])[:1] + (f["forecast"].get("years") or [])[-1:],
            "fcff_cr": (f["forecast"].get("fcff_cr") or [])[:1] + (f["forecast"].get("fcff_cr") or [])[-1:],
        }
        prompt = f"{_EXPLAIN_SYS}\n\nDCF JSON:\n{json.dumps(slim, default=str)}\n\nQuestion: {question}"
        resp = _client.models.generate_content(
            model=DEFAULT_TEXT_MODEL, contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=320, thinking_config=types.ThinkingConfig(thinking_budget=0)),
        )
        return (resp.text or "").strip() or None
    except Exception as e:  # noqa: BLE001
        logger.warning(f"dcf explain model call failed: {type(e).__name__}: {e}")
        return None


def _allowed_numbers(f: Dict[str, Any]) -> List[float]:
    vals: List[float] = []

    def walk(o: Any) -> None:
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, (int, float)) and not isinstance(o, bool):
            vals.append(float(o))
    walk(f)
    # derived: crore values also appear in lakh crore; differences between per-share values
    extra = [abs(f["intrinsic_inr"] - f["market_inr"])] + [v / 1e5 for v in vals if abs(v) >= 1e4]
    return vals + extra


def grounded(text: str, f: Dict[str, Any]) -> bool:
    """Every number in `text` must match a number in the DCF facts (rounded), except small counts and FY labels."""
    allowed = _allowed_numbers(f)
    for m in re.finditer(r"(?<![A-Za-z])(\d[\d,]*\.?\d*)", text):
        raw = m.group(1).replace(",", "").rstrip(".")
        if not raw:
            continue
        try:
            x = float(raw)
        except ValueError:
            continue
        ctx = text[max(0, m.start() - 2): m.start()]
        if x <= 10 and float(x).is_integer():
            continue  # counts ("three drivers", "2-4 years")
        if ctx.endswith("FY") or (1990 <= x <= 2100 and float(x).is_integer()):
            continue
        if not any(abs(x - a) <= max(0.051, abs(a) * 0.006) or abs(x - round(a)) < 0.51 or abs(x - round(a, 1)) < 0.051 for a in allowed):
            return False
    return True


def _explain_fallback(f: Dict[str, Any], topic: str) -> str:
    if topic == "wacc":
        w = f["wacc"]
        return (f"The WACC of {w.get('wacc_pct', 0):.2f}% combines a cost of equity of {w.get('ke_pct', 0):.2f}% (risk-free {w.get('rf_used_pct', 0):.2f}% plus beta "
                f"{w.get('beta_adj', 0):.2f} times an equity premium of {w.get('erp_total_pct', 0):.2f}%) at a {w.get('weight_equity', 0) * 100:.0f}% weight, and an after-tax "
                f"cost of debt of {w.get('kd_after_tax_pct', 0):.2f}% at {w.get('weight_debt', 0) * 100:.0f}%.")
    if topic == "terminal":
        t = f["terminal"]
        return (f"Terminal value is {_cr(t['pv_tv_cr'])} in today's money, {f.get('tv_share_of_ev_pct') or 0:.0f}% of enterprise value, at {t.get('g_pct')}% growth. "
                f"An exit multiple of {t.get('exit_multiple')}x EBITDA would imply about {t['implied_g_from_exit_pct']:.1f}% growth"
                + (", so the two methods diverge and the terminal value is a key judgement." if t.get("methods_diverge") else "."))
    if topic == "forecast":
        fc = f["forecast"]
        ys, ff = fc.get("years") or [], fc.get("fcff_cr") or []
        if ys and ff:
            return f"Free cash flow runs from {_cr(ff[0])} in {ys[0]} to {_cr(ff[-1])} in {ys[-1]}; discounted, the forecast years are worth {_cr(f['pv_fcff_cr'])} today."
    gap = f["market_inr"] - f["intrinsic_inr"]
    return (f"The model values ONGC at ₹{f['intrinsic_inr']:.2f} per share against a market price of ₹{f['market_inr']:.2f}, so it looks {f['verdict']} by "
            f"{abs(f['upside_pct']):.1f}%. Enterprise value is {_cr(f['ev_cr'])} ({_cr(f['pv_fcff_cr'])} from forecast cash flows and {_cr(f['pv_tv_cr'])} from terminal value); "
            f"after debt, leases and decommissioning provisions, and adding cash, SRF deposits and listed investments, equity value is {_cr(f['equity_cr'])}. "
            + (f"The market prices about ₹{gap:.0f} per share more than the model." if gap > 0 else ""))


def answer_explain(question: str, f: Dict[str, Any], topic: str, turn_id: str, persona: str, language: str, t0: float) -> Dict[str, Any]:
    text = _gemini_explain(question, f)
    used_model = bool(text) and grounded(text, f)
    if not used_model:
        if text:
            logger.info("dcf explain: model answer rejected (number not in the DCF); using the deterministic explanation")
        text = _explain_fallback(f, topic)
    insights = [
        f"Intrinsic ₹{f['intrinsic_inr']:.2f} vs market ₹{f['market_inr']:.2f} ({f['upside_pct']:+.1f}%, {f['verdict']}).",
        f"EV {_cr(f['ev_cr'])} = forecast cash flows {_cr(f['pv_fcff_cr'])} + terminal value {_cr(f['pv_tv_cr'])}.",
        f"WACC {f['wacc'].get('wacc_pct', 0):.2f}% · terminal growth {f['terminal'].get('g_pct')}% · Brent ${_f(f['assumptions'].get('brent_usd')):.0f}.",
    ]
    return _base_contract(turn_id, persona, language, t0, text, _topic_visual(f, topic), insights,
                          ["What drives the valuation?", "What if WACC is 12%?", "What if Brent is $60?"],
                          "Explained from this conversation's DCF run" + (" (model-written, number-checked)" if used_model else ""))


_FIELD_NAMES = {"wacc_pct": ("WACC", "%"), "terminal_g_pct": ("Terminal growth", "%"), "brent_usd": ("Brent", "$/bbl"), "capex_scale_pct": ("Capex scale", "% of base plan"),
                "production_decline_pct": ("Production decline", "%/yr"), "holdco_discount_pct": ("Holdco discount", "%"), "fx_inr_usd": ("Rupee per dollar", "₹/$")}


def run_whatif(dcf: Dict[str, Any], overrides: Dict[str, float]) -> Dict[str, Any]:
    from app.agents.dcf_agent import build_dcf_assumptions_from_inputs
    from app.finance.dcf.assumptions import AssumptionField
    from app.finance.dcf.run import run_dcf

    base_inputs = dict(dcf.get("inputs") or {})
    engine_inputs = {**base_inputs, **{k: v for k, v in overrides.items() if k != "fx_inr_usd"}}
    asm = build_dcf_assumptions_from_inputs(f"whatif-{int(time.time())}", engine_inputs)
    if "fx_inr_usd" in overrides:
        asm = asm.model_copy(update={"fx_inr_usd": AssumptionField(value=float(overrides["fx_inr_usd"]), source=asm.fx_inr_usd.source, edited_by_user=True)})
    if asm.terminal_g_pct.value >= asm.wacc_pct.value - 1:
        raise ValueError("Terminal growth must be at least 1 point below WACC.")
    return run_dcf(asm)


def answer_whatif(question: str, dcf: Dict[str, Any], overrides: Dict[str, float], turn_id: str, persona: str, language: str, t0: float) -> Dict[str, Any]:
    base = facts_from_visual(dcf["visual"])
    res = run_whatif(dcf, overrides)
    new_iv = float(res["per_share"]["intrinsic_inr"])
    base_iv, mkt = base["intrinsic_inr"], base["market_inr"]
    chg = (new_iv - base_iv) / base_iv * 100 if base_iv else 0.0
    up = (new_iv - mkt) / mkt * 100 if mkt else 0.0
    changes = []
    for k, v in overrides.items():
        name, unit = _FIELD_NAMES.get(k, (k, ""))
        bv = base["assumptions"].get(k)
        if bv is None:
            bv = _base_value(dcf["visual"], k)
        def fmt(x: float) -> str:
            return f"{x:.2f}".rstrip("0").rstrip(".")

        if unit.startswith("%"):
            changes.append(f"{name} {fmt(_f(bv))}% → {fmt(v)}{unit}")
        elif unit == "$/bbl":
            changes.append(f"{name} ${fmt(_f(bv))} → ${fmt(v)}/bbl")
        elif unit == "₹/$":
            changes.append(f"{name} ₹{fmt(_f(bv))} → ₹{fmt(v)}")
        else:
            changes.append(f"{name} {fmt(_f(bv))} → {fmt(v)} {unit}")
    spoken = (
        f"With {', '.join(changes)}, the DCF value moves from ₹{base_iv:.0f} to ₹{new_iv:.0f} per share ({chg:+.0f}%), "
        f"{'above' if new_iv > mkt else 'below'} the market price of ₹{mkt:.0f} ({up:+.0f}%)."
    )
    visual = {"type": "kpi", "mode": "replace", "title": f"What-if: {'; '.join(changes)}",
              "kpis": [{"label": "Base case value", "value": round(base_iv, 2), "unit": "₹/share"},
                       {"label": "Scenario value", "value": round(new_iv, 2), "unit": "₹/share", "delta": f"{chg:+.1f}% vs base"},
                       {"label": "Market price", "value": round(mkt, 2), "unit": "₹/share", "delta": f"scenario {up:+.1f}% vs market"}]}
    new_bridge = {b["label"]: _f(b["value_inr_cr"]) for b in res.get("bridge") or []}
    insights = [
        f"Scenario value ₹{new_iv:.2f} vs base ₹{base_iv:.2f} ({chg:+.1f}%); market ₹{mkt:.2f}.",
        f"Enterprise value {_cr(base['ev_cr'])} → {_cr(new_bridge.get('Enterprise Value (EV)', 0))}.",
        "Only the stated inputs changed; everything else is the base case. The base DCF stays the reference for later questions.",
    ]
    return _base_contract(turn_id, persona, language, t0, spoken, visual, insights,
                          ["What drives the valuation?", "What if Brent is $60?", "What if terminal growth is 2%?"],
                          f"Re-ran the DCF engine with {len(overrides)} changed input(s)")


def answer_dcf_followup(req: Dict[str, Any], query: str, persona: str, turn_id: str, language: str, t0: float) -> Dict[str, Any]:
    dcf = req["dcf"]
    if req["intent"] == "whatif":
        return answer_whatif(query, dcf, req["overrides"], turn_id, persona, language, t0)
    f = facts_from_visual(dcf["visual"])
    if req["intent"] == "drivers" and f["drivers"]:
        return answer_drivers(f, turn_id, persona, language, t0)
    return answer_explain(query, f, req.get("topic") or "summary", turn_id, persona, language, t0)


async def answer_dcf_followup_async(req: Dict[str, Any], query: str, persona: str, turn_id: str, language: str, t0: float) -> Dict[str, Any]:
    return await asyncio.to_thread(answer_dcf_followup, req, query, persona, turn_id, language, t0)
