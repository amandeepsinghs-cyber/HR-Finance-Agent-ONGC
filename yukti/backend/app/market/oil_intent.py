"""Direct crude-oil price questions (26-Oct): "plot the Brent oil price for the past 5 years", "WTI trend", "what is the
Brent price". The data planner only knows ONGC data, so these used to fall through to "please rephrase". Answered from
the saved daily history + live Yahoo Finance updates (app.market.oil_prices): a daily line chart ending with today's
live price, KPIs and a deterministic summary.
Questions that combine oil with ONGC metrics (revenue, PAT…), what-if scenarios and screen commands are left alone.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.market.oil_prices import get_daily_history, get_oil_prices, normalize_benchmark

_OIL = re.compile(r"\b(brent|wti|west texas|crude oil price|crude price|oil price|oil prices|crude prices|price of (crude|oil)|rupee|usd ?inr|inr|dollar rate|exchange rate|forex|rupee vs (the )?dollar)\b", re.I)
_ASK = re.compile(r"\b(plot|chart|graph|trend|show|display|history|historical|movement|moved|price|prices|how has|what is|what's|current|today|latest|past|last)\b", re.I)
# leave these to other paths: ONGC metrics (use the overlay), what-if / sensitivity, screen commands
_NOT = re.compile(
    r"\b(revenue|pat|profit|ebitda|income|realisation|realization|margin|cash ?flow|balance sheet|p&l|"
    r"what[- ]if|scenario|sensitivity|impact|if brent|if oil|dcf|valuation|"
    r"overlay|superimpose|on top|remove|hide|export|download)\b",
    re.I,
)
_WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def detect_oil_plot(query: str) -> Optional[Dict[str, Any]]:
    q = (query or "").strip()
    if not q or not _OIL.search(q) or not _ASK.search(q) or _NOT.search(q):
        return None
    months = 60
    m = re.search(r"\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)\s*(years?|yrs?)\b", q, re.I)
    if m:
        n = m.group(1).lower()
        months = 12 * (int(n) if n.isdigit() else _WORDNUM[n])
    else:
        m = re.search(r"\b(\d{1,2})\s*months?\b", q, re.I)
        if m:
            months = int(m.group(1))
        elif re.search(r"\b(a|one|past|last)\s+year\b", q, re.I):
            months = 12
    months = max(3, min(months, 120))
    if re.search(r"\b(rupee|usd ?inr|inr|dollar rate|exchange rate|forex)\b", q, re.I) and not re.search(r"\b(brent|wti|crude|oil)\b", q, re.I):
        bench = "inr"
    else:
        bench = "wti" if re.search(r"\b(wti|west texas)\b", q, re.I) else "brent"
    return {"benchmark": normalize_benchmark(bench), "months": months}


def _day_label(d: str) -> str:
    return datetime.strptime(d, "%Y-%m-%d").strftime("%d %b %Y")


def build_oil_plot_contract(req: Dict[str, Any], persona: str, turn_id: str, language: str, t0: float) -> Dict[str, Any]:
    d = get_oil_prices(req["benchmark"])
    hist = get_daily_history(req["benchmark"])
    months = req["months"]
    cutoff = (datetime.now(timezone.utc) - timedelta(days=round(months * 30.44))).strftime("%Y-%m-%d")
    days = [(k, v) for k, v in sorted(hist.items()) if k >= cutoff]
    if not days:
        raise RuntimeError("No oil price history for that period.")
    short = d["short"]
    cur = "₹" if d["benchmark"] == "inr" else "$"  # 27-Oct: the rupee uses the same path
    per = "per dollar" if d["benchmark"] == "inr" else "a barrel"
    key = "inr_per_usd" if d["benchmark"] == "inr" else f"{d['benchmark']}_usd_bbl"
    live = d["live"]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = [{"date": _day_label(k), key: v} for k, v in days]
    # today's live price as the last point (if the market has moved since the last daily close)
    live_point = bool(live.get("price")) and not d.get("stale")
    if live_point:
        if days[-1][0] == today:
            rows[-1] = {"date": "Today (live)", key: live["price"]}
        else:
            rows.append({"date": "Today (live)", key: live["price"]})
    vals = [r[key] for r in rows]
    hi_i = max(range(len(vals)), key=lambda i: vals[i])
    lo_i = min(range(len(vals)), key=lambda i: vals[i])
    yrs = months // 12
    period = f"last {yrs} years" if months % 12 == 0 and yrs > 1 else ("last 12 months" if months == 12 else f"last {months} months")
    title = f"{d['label']}{'' if d['benchmark'] == 'inr' else ' price'}, daily · {rows[0]['date']} – {_day_label(today)}"
    chg = (vals[-1] - vals[0]) / vals[0] * 100 if vals[0] else 0
    stale = " (from saved history; the live feed is unavailable right now)" if d.get("stale") else ""
    hist_info = d.get("history") or {}
    spoken = (
        f"{'The rupee' if d['benchmark'] == 'inr' else short} is at {cur}{live['price']:.2f} {per} today{stale}"
        + (f", {'up' if (live.get('change_pct') or 0) >= 0 else 'down'} {abs(live.get('change_pct') or 0):.1f}% on the day" if live.get("change_pct") is not None and not d.get("stale") else "")
        + f". Over the {period} it moved from {cur}{vals[0]:.2f} on {rows[0]['date']}, peaking at {cur}{vals[hi_i]:.2f} on {rows[hi_i]['date']} "
        f"and bottoming at {cur}{vals[lo_i]:.2f} on {rows[lo_i]['date']}."
    )
    insights = [
        f"Change over the period: {'+' if chg >= 0 else ''}{chg:.0f}% ({rows[0]['date']} to today).",
        f"Range: {cur}{vals[lo_i]:.2f} ({rows[lo_i]['date']}) to {cur}{vals[hi_i]:.2f} ({rows[hi_i]['date']}).",
        ("Tip: ask \"why did revenue hold up while oil fell?\" to see the rupee's effect on ONGC's revenue." if d["benchmark"] == "inr"
         else "Tip: ask for ONGC revenue by year and say \"overlay Brent\" to compare the two."),
    ]
    status = (
        f"Live {d['label']} prices: {hist_info.get('saved_days', 0):,} days from saved history + "
        f"{hist_info.get('new_days', 0)} new day(s) fetched from Yahoo Finance"
        if not d.get("stale") else f"Yahoo Finance unreachable: served {len(hist):,} days from saved history"
    )
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
            "subtitle": f"{period.capitalize()} · daily closes + today's live price · Yahoo Finance ({d['symbol']})",
            "table": {"columns": ["date", key], "rows": rows, "total_rows": len(rows), "masking": {"level": "none"}},
            "chart": {
                "kind": "line",
                "data": rows,
                "x": "date",
                "y": key,
                "category": "date",
                "value": key,
                "title": title,
                "unit": d["unit"],
            },
            "kpis": [
                {"label": f"{short} today (live)" if not d.get("stale") else f"{short} last close", "value": live["price"] if live.get("price") else vals[-1], "unit": d["unit"],
                 "delta": (f"{'▲' if (live.get('change_pct') or 0) >= 0 else '▼'} {abs(live.get('change_pct') or 0):.1f}% today") if live.get("change_pct") is not None and not d.get("stale") else "saved history"},
                {"label": f"Highest · {rows[hi_i]['date']}", "value": vals[hi_i], "unit": d["unit"]},
                {"label": f"Lowest · {rows[lo_i]['date']}", "value": vals[lo_i], "unit": d["unit"]},
            ],
        },
        "insights": insights,
        # own takeaways (otherwise the generic engine adds "x% of the total"-style lines that make no sense for prices)
        "insights_v2": [
            {"kind": "trend", "text": insights[0]},
            {"kind": "comparison", "text": insights[1]},
            {"kind": "note", "text": insights[2]},
        ],
        "context_chips": [
            {"label": persona, "kind": "role"},
            {"label": period.capitalize(), "kind": "period"},
            {"label": f"Daily · {d['unit']}", "kind": "filter"},
            {"label": f"Yahoo Finance {d['symbol']}", "kind": "source"},
        ],
        "sources": [{"kind": "data", "object": f"Yahoo Finance {d['symbol']} ({d['label']}, front-month futures)", "sql": d["source"]}],
        "suggestions": ["Show ONGC revenue for the last 10 years", ("Plot Brent for the same period" if d["benchmark"] != "brent" else "Plot the rupee against the dollar for the same period")],
        "access": {"status": "allowed"},
        "export_options": ["xlsx", "pdf", "sheets"],
        "status_events": [status],
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
    }
