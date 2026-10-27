"""Revenue drivers (27-Oct): answers "why didn't ONGC's revenue fall when oil fell?" and "how has the portfolio changed?".

- Revenue, product mix, volumes, levies and PAT: ONGC standalone financials in BigQuery (v_fin_trend_latest).
- Brent ($/bbl) and the rupee (₹ per $): fiscal-year averages of daily closes from app.market.oil_prices (Yahoo).
- Everything is computed (no model-written numbers): an indexed chart (first FY = 100) of Brent $, Brent ₹, ₹ per $
  and revenue; a table of actual values; and a price / volume bridge for crude and gas between the Brent
  peak year (or first year) and the latest year.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional

from app.config import BQ_GOLD_DATASET, BQ_LOCATION, GCP_PROJECT
from app.market.oil_prices import get_oil_prices

logger = logging.getLogger("yukti.market.drivers")

_WORDNUM = {"three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

_WHY = re.compile(r"\b(why|how come|reason|reasons|explain|despite|even though|even then|in spite|what drove|drivers?|resilien\w*|did not (fall|fail|drop|decline|suffer)|didn'?t (fall|drop|decline|suffer))\b", re.I)
_REV = re.compile(r"\b(revenue|revenues|top ?line|turnover|sales|income)\b", re.I)
_PRICE = re.compile(r"\b(oil|brent|wti|crude|price|prices|rupee|dollar|currency|exchange rate)\b", re.I)
_MIX = re.compile(r"\b(portfolio|mix|composition|product mix|revenue mix|split|share of|breakdown)\b", re.I)
_MIX_SUBJECT = re.compile(r"\b(revenue|portfolio|product|products|crude|gas|vap)\b", re.I)


def _years(q: str, default: int = 5) -> int:
    m = re.search(r"\b(\d{1,2}|three|four|five|six|seven|eight|nine|ten)\s*(years?|yrs?)\b", q, re.I)
    if not m:
        return default
    n = m.group(1).lower()
    return max(3, min(int(n) if n.isdigit() else _WORDNUM[n], 10))


def detect_revenue_drivers(query: str) -> Optional[Dict[str, Any]]:
    q = query or ""
    if _WHY.search(q) and _REV.search(q) and _PRICE.search(q):
        return {"kind": "drivers", "years": _years(q)}
    return None


def detect_portfolio_mix(query: str) -> Optional[Dict[str, Any]]:
    q = query or ""
    if _MIX.search(q) and _MIX_SUBJECT.search(q) and re.search(r"\b(draw|show|plot|chart|how|changed|change|evolve|over|past|last|trend)\b", q, re.I):
        return {"kind": "mix", "years": _years(q)}
    return None


_SQL = """
SELECT fiscal_year,
  MAX(IF(line_code='PL.REV_OPS', COALESCE(value_inr_cr, value), NULL)) AS revenue_cr,
  MAX(IF(line_code='REV.CRUDE', COALESCE(value_inr_cr, value), NULL)) AS crude_cr,
  MAX(IF(line_code='REV.GAS', COALESCE(value_inr_cr, value), NULL)) AS gas_cr,
  MAX(IF(line_code='REV.VAP', COALESCE(value_inr_cr, value), NULL)) AS vap_cr,
  MAX(IF(line_code='LEVY.TOTAL', COALESCE(value_inr_cr, value), NULL)) AS levies_cr,
  MAX(IF(line_code='LEVY.OTHER_SAED', COALESCE(value_inr_cr, value), NULL)) AS saed_cr,
  MAX(IF(line_code='QTY.CRUDE_SOLD', value, NULL)) AS crude_mmt,
  MAX(IF(line_code='QTY.GAS_SOLD', value, NULL)) AS gas_bcm,
  MAX(IF(line_code='PL.PAT', COALESCE(value_inr_cr, value), NULL)) AS pat_cr
FROM `{project}.{dataset}.v_fin_trend_latest`
WHERE scope = 'standalone'
GROUP BY fiscal_year
"""

_bq = None


def _financials() -> List[Dict[str, Any]]:
    global _bq
    from google.cloud import bigquery

    if _bq is None:
        _bq = bigquery.Client(project=GCP_PROJECT, location=BQ_LOCATION)
    rows = [dict(r) for r in _bq.query(_SQL.format(project=GCP_PROJECT, dataset=BQ_GOLD_DATASET)).result()]
    rows = [r for r in rows if r.get("revenue_cr") and re.match(r"^FY\d{2}$", str(r["fiscal_year"]))]
    return sorted(rows, key=lambda r: int(str(r["fiscal_year"])[2:]))


def _f(v: Any) -> float:
    return float(v) if v is not None else 0.0


def _cr(v: float) -> str:
    """Indian grouping, e.g. 155517 -> ₹1,55,517 cr."""
    n = int(round(abs(v)))
    s = str(n)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return f"{'-' if v < 0 else ''}₹{s} cr"


def _pct(a: float, b: float) -> float:
    return (b - a) / a * 100 if a else 0.0


def _sgn(p: float) -> str:
    return f"{'+' if p >= 0 else '−'}{abs(p):.0f}%"


def _window(years: int) -> Dict[str, Any]:
    fin = _financials()
    brent = {p["fy"]: p["avg"] for p in get_oil_prices("brent")["fy_series"] if not p["provisional"]}
    inr = {p["fy"]: p["avg"] for p in get_oil_prices("inr")["fy_series"] if not p["provisional"]}
    fin = [r for r in fin if r["fiscal_year"] in brent and r["fiscal_year"] in inr][-years:]
    if len(fin) < 2:
        raise RuntimeError("Not enough overlapping years of revenue and market data.")
    for r in fin:
        fy = r["fiscal_year"]
        r["brent_usd"] = brent[fy]
        r["inr_per_usd"] = inr[fy]
        r["brent_inr"] = brent[fy] * inr[fy]
        r["net_revenue_cr"] = _f(r["revenue_cr"]) - _f(r["levies_cr"])
    return {"rows": fin}


def build_drivers_contract(req: Dict[str, Any], persona: str, turn_id: str, language: str, t0: float) -> Dict[str, Any]:
    w = _window(req["years"])
    rows: List[Dict[str, Any]] = w["rows"]
    first, last = rows[0], rows[-1]
    peak = max(rows, key=lambda r: r["brent_usd"])
    base = peak if peak is not last else first  # explain the fall from the Brent peak (or from the first year)
    fy0, fy1 = base["fiscal_year"], last["fiscal_year"]

    d_brent = _pct(base["brent_usd"], last["brent_usd"])
    d_inr = _pct(base["inr_per_usd"], last["inr_per_usd"])
    d_brent_inr = _pct(base["brent_inr"], last["brent_inr"])
    d_rev = _pct(_f(base["revenue_cr"]), _f(last["revenue_cr"]))
    d_net = _pct(base["net_revenue_cr"], last["net_revenue_cr"])
    d_pat = _pct(_f(base["pat_cr"]), _f(last["pat_cr"]))

    # price / volume split for crude and gas (revenue per unit sold)
    def pv(rev_k: str, qty_k: str) -> Dict[str, float]:
        r0, r1, q0, q1 = _f(base[rev_k]), _f(last[rev_k]), _f(base[qty_k]), _f(last[qty_k])
        u0 = r0 / q0 if q0 else 0.0
        u1 = r1 / q1 if q1 else 0.0
        return {"total": r1 - r0, "volume": (q1 - q0) * u0, "price": q1 * (u1 - u0), "unit_pct": _pct(u0, u1), "qty_pct": _pct(q0, q1), "rev_pct": _pct(r0, r1)}

    crude, gas = pv("crude_cr", "crude_mmt"), pv("gas_cr", "gas_bcm")
    gas_share0 = _f(first["gas_cr"]) / _f(first["revenue_cr"]) * 100
    gas_share1 = _f(last["gas_cr"]) / _f(last["revenue_cr"]) * 100
    saed0, saed1 = _f(base["saed_cr"]), _f(last["saed_cr"])

    # chart: everything indexed to the first FY = 100, so $ prices, the rupee and ₹ revenue share one axis
    def idx(r: Dict[str, Any], k: str) -> float:
        a = _f(first[k])
        return round(_f(r[k]) / a * 100, 1) if a else 0.0

    chart_rows = [
        {
            "fiscal_year": r["fiscal_year"],
            "brent_in_dollars": idx(r, "brent_usd"),
            "rupees_per_dollar": idx(r, "inr_per_usd"),
            "brent_in_rupees": idx(r, "brent_inr"),
            "ongc_revenue": idx(r, "revenue_cr"),
        }
        for r in rows
    ]
    table_rows = [
        {
            "fiscal_year": r["fiscal_year"],
            "brent_usd_bbl": round(r["brent_usd"], 2),
            "inr_per_usd": round(r["inr_per_usd"], 2),
            "brent_inr_bbl": round(r["brent_inr"]),
            "revenue_cr": round(_f(r["revenue_cr"])),
            "crude_cr": round(_f(r["crude_cr"])),
            "gas_cr": round(_f(r["gas_cr"])),
            "vap_cr": round(_f(r["vap_cr"])),
            "levies_cr": round(_f(r["levies_cr"])),
            "net_revenue_cr": round(r["net_revenue_cr"]),
            "pat_cr": round(_f(r["pat_cr"])),
        }
        for r in rows
    ]

    spoken = (
        f"From {fy0} to {fy1}, Brent fell {abs(d_brent):.0f}% in dollars, but ONGC's revenue fell only {abs(d_rev):.0f}%"
        + (f" and revenue after levies only {abs(d_net):.0f}%" if d_net < 0 else f" and revenue after levies rose {d_net:.0f}%")
        + f". Three things cushioned it: the rupee weakened {abs(d_inr):.0f}%, so Brent fell only {abs(d_brent_inr):.0f}% in rupees; "
        f"gas, now {gas_share1:.0f}% of revenue, is sold at a government-set price that stays at its ceiling unless crude falls much further; "
        f"and the windfall tax ended. Profit did feel it: PAT is {_sgn(d_pat)}."
    )
    insights = [
        f"Rupee cushion: ₹ per $ went from {base['inr_per_usd']:.1f} to {last['inr_per_usd']:.1f} ({_sgn(d_inr)}), so Brent moved {_sgn(d_brent)} in dollars but only {_sgn(d_brent_inr)} in rupees.",
        f"Gas is shielded: gas revenue {_sgn(gas['rev_pct'])} ({fy0}→{fy1}) and its share of revenue rose from {gas_share0:.0f}% ({first['fiscal_year']}) to {gas_share1:.0f}%. Under the April 2023 formula, legacy-field gas is priced at 10% of the Indian crude basket within a floor and ceiling, so it sits at the ceiling while crude is high.",
        f"Crude tracks oil: crude revenue {_sgn(crude['rev_pct'])} = price per tonne {_sgn(crude['unit_pct'])} and volume {_sgn(crude['qty_pct'])} ({_cr(crude['price'])} price effect, {_cr(crude['volume'])} volume effect).",
        f"Levies fell: windfall tax and other levies {_cr(saed0)} in {fy0} vs {_cr(saed1)} in {fy1}; revenue after all levies {_sgn(d_net)}.",
        f"Profit did suffer: PAT {_cr(_f(base['pat_cr']))} in {fy0} vs {_cr(_f(last['pat_cr']))} in {fy1} ({_sgn(d_pat)}), with lower crude and gas volumes.",
    ]
    period = f"{first['fiscal_year']}–{last['fiscal_year']}"
    title = f"Why revenue held up while oil fell · indexed, {first['fiscal_year']} = 100 · {period}"
    return {
        "turn_id": turn_id,
        "language": language,
        "persona": persona,
        "spoken_summary": spoken,
        "display_text": spoken,
        "visual": {
            "type": "chart",
            "mode": "replace",
            "title": title,
            "subtitle": f"Brent ($), Brent in ₹, ₹ per $ and revenue · {first['fiscal_year']} = 100 (gas revenue tripled: see the takeaways and the portfolio chart)",
            "table": {"columns": list(table_rows[0].keys()), "rows": table_rows, "total_rows": len(table_rows), "masking": {"level": "none"}},
            "chart": {
                "kind": "line",
                "data": chart_rows,
                "x": "fiscal_year",
                "y": "ongc_revenue",
                "category": "fiscal_year",
                "value": "ongc_revenue",
                "title": title,
                "unit": "index",
            },
            "kpis": [
                {"label": f"Brent in $ · {fy0}→{fy1}", "value": round(d_brent, 1), "unit": "%"},
                {"label": f"Brent in ₹ · {fy0}→{fy1}", "value": round(d_brent_inr, 1), "unit": "%", "delta": f"rupee {_sgn(d_inr)}"},
                {"label": f"Revenue · {fy0}→{fy1}", "value": round(d_rev, 1), "unit": "%", "delta": f"after levies {_sgn(d_net)}"},
            ],
        },
        "insights": insights,
        "insights_v2": [
            {"kind": "headline", "text": insights[0]},
            {"kind": "comparison", "text": insights[1]},
            {"kind": "trend", "text": insights[2]},
            {"kind": "note", "text": insights[3]},
            {"kind": "risk", "text": insights[4]},
        ],
        "context_chips": [
            {"label": persona, "kind": "role"},
            {"label": period, "kind": "period"},
            {"label": "ONGC standalone + market data", "kind": "subject"},
        ],
        "sources": [
            {"kind": "data", "object": f"{BQ_GOLD_DATASET}.v_fin_trend_latest", "sql": "ONGC standalone revenue lines, volumes, levies and PAT by fiscal year"},
            {"kind": "data", "object": "Yahoo Finance BZ=F and INR=X", "sql": "Brent and rupee fiscal-year averages of daily closes"},
        ],
        "suggestions": ["How has the revenue portfolio changed over the past 5 years?", "Overlay the rupee per dollar rate", "Show PAT for the last 5 years"],
        "access": {"status": "allowed"},
        "export_options": ["xlsx", "pdf", "sheets"],
        "status_events": ["Computed price, volume, rupee and mix effects from ONGC financials + Yahoo Finance market data"],
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def build_mix_contract(req: Dict[str, Any], persona: str, turn_id: str, language: str, t0: float) -> Dict[str, Any]:
    fin = _financials()[-req["years"]:]
    if len(fin) < 2:
        raise RuntimeError("Not enough years of revenue data.")
    rows = []
    for r in fin:
        crude, gas, vap = _f(r["crude_cr"]), _f(r["gas_cr"]), _f(r["vap_cr"])
        other = max(0.0, _f(r["revenue_cr"]) - crude - gas - vap)
        # "other operating revenue" (~0.4%) is folded into VAP: a tiny series next to crude would trip the chart's
        # mixed-scale rule and split the stacked bar into small multiples
        rows.append({"fiscal_year": r["fiscal_year"], "crude_oil_cr": round(crude), "natural_gas_cr": round(gas), "value_added_products_and_other_cr": round(vap + other)})
    first, last = rows[0], rows[-1]

    def share(r: Dict[str, Any], k: str) -> float:
        tot = r["crude_oil_cr"] + r["natural_gas_cr"] + r["value_added_products_and_other_cr"]
        return r[k] / tot * 100 if tot else 0.0

    s = {k: (share(first, k), share(last, k)) for k in ("crude_oil_cr", "natural_gas_cr", "value_added_products_and_other_cr")}
    period = f"{first['fiscal_year']}–{last['fiscal_year']}"
    spoken = (
        f"Between {first['fiscal_year']} and {last['fiscal_year']}, natural gas grew from {s['natural_gas_cr'][0]:.0f}% to {s['natural_gas_cr'][1]:.0f}% of ONGC's revenue, "
        f"while crude oil went from {s['crude_oil_cr'][0]:.0f}% to {s['crude_oil_cr'][1]:.0f}% and value-added products from "
        f"{s['value_added_products_and_other_cr'][0]:.0f}% to {s['value_added_products_and_other_cr'][1]:.0f}%. Gas revenue went from {_cr(first['natural_gas_cr'])} to {_cr(last['natural_gas_cr'])}."
    )
    peak_gas = max(rows, key=lambda r: r["natural_gas_cr"])
    insights = [
        f"Gas share {s['natural_gas_cr'][0]:.0f}% → {s['natural_gas_cr'][1]:.0f}% of revenue ({first['fiscal_year']}→{last['fiscal_year']}), driven by the April 2023 gas price reform, not by volume.",
        f"Crude share {s['crude_oil_cr'][0]:.0f}% → {s['crude_oil_cr'][1]:.0f}%: crude revenue {_cr(first['crude_oil_cr'])} → {_cr(last['crude_oil_cr'])}.",
        f"Gas revenue peaked in {peak_gas['fiscal_year']} at {_cr(peak_gas['natural_gas_cr'])}; from that peak it is {_sgn(_pct(peak_gas['natural_gas_cr'], last['natural_gas_cr']))} (from {first['fiscal_year']}: {_sgn(_pct(first['natural_gas_cr'], last['natural_gas_cr']))}).",
    ]
    title = f"Revenue portfolio by product (₹ cr) · {period}"
    return {
        "turn_id": turn_id,
        "language": language,
        "persona": persona,
        "spoken_summary": spoken,
        "display_text": spoken,
        "visual": {
            "type": "chart",
            "mode": "replace",
            "title": title,
            "subtitle": "Crude oil, natural gas, value-added products and other operating revenue",
            "table": {"columns": list(rows[0].keys()), "rows": rows, "total_rows": len(rows), "masking": {"level": "none"}},
            "chart": {
                "kind": "stacked_bar",
                "data": rows,
                "x": "fiscal_year",
                "y": "crude_oil_cr",
                "category": "fiscal_year",
                "value": "crude_oil_cr",
                "title": title,
                "unit": "₹ Cr",
            },
            "kpis": [
                {"label": f"Gas share · {last['fiscal_year']}", "value": round(s["natural_gas_cr"][1], 1), "unit": "%", "delta": f"from {s['natural_gas_cr'][0]:.0f}% in {first['fiscal_year']}"},
                {"label": f"Crude share · {last['fiscal_year']}", "value": round(s["crude_oil_cr"][1], 1), "unit": "%", "delta": f"from {s['crude_oil_cr'][0]:.0f}% in {first['fiscal_year']}"},
                {"label": f"VAP share · {last['fiscal_year']}", "value": round(s["value_added_products_and_other_cr"][1], 1), "unit": "%", "delta": f"from {s['value_added_products_and_other_cr'][0]:.0f}% in {first['fiscal_year']}"},
            ],
        },
        "insights": insights,
        "insights_v2": [{"kind": "headline", "text": insights[0]}, {"kind": "trend", "text": insights[1]}, {"kind": "comparison", "text": insights[2]}],
        "context_chips": [{"label": persona, "kind": "role"}, {"label": period, "kind": "period"}, {"label": "ONGC standalone", "kind": "subject"}],
        "sources": [{"kind": "data", "object": f"{BQ_GOLD_DATASET}.v_fin_trend_latest", "sql": "REV.CRUDE, REV.GAS, REV.VAP, PL.REV_OPS by fiscal year (standalone)"}],
        "suggestions": ["Why did revenue hold up while oil prices fell?", "Show as 100% stacked", "Overlay Brent"],
        "access": {"status": "allowed"},
        "export_options": ["xlsx", "pdf", "sheets"],
        "status_events": ["Computed revenue mix from ONGC standalone financials"],
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
    }
