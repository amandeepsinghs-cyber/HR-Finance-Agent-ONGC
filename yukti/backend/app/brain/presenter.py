"""Presenter (B2): result -> visual, deterministic narration, context chips.

Numbers in the narration come only from the query result (BUILD.md principle 1). B4 adds
the insight library, drill-down chips and the numeric-grounding check on top of this.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.brain.compiler import CompiledQuery, QueryResult
from app.brain.query_spec import QuerySpec
from app.semantic.entities import get_entities
from app.tools.chart_rules import build_chart_spec, select_chart_kind

UNIT_WORDS = {"employees": "employees", "posts": "posts", "workers": "contract workers", "inr_cr": "₹ crore",
              "inr_lakh": "₹ lakh", "usd_per_boe": "$/BOE", "inr_per_boe": "₹/BOE", "pct": "%", "years": "years", "hours": "hours",
              "boe": "BOE", "mmtoe": "MMTOE", "incidents": "incidents", "ratio": "", "score": "", "parameters": "parameters"}
CHART_UNIT = {"employees": "employees", "posts": "employees", "workers": "employees", "inr_cr": "₹ Cr",
              "inr_lakh": "₹ Lakh", "usd_per_boe": "$/BOE", "pct": "%", "years": "years", "hours": "hours"}
DIM_PLURAL = {"discipline": "disciplines", "work_centre": "work centres", "grade": "grades", "field": "fields",
              "asset": "assets", "fiscal_year": "years", "cadre": "cadres", "gender": "groups"}


def _num(v: Any) -> float:
    """Numeric value of a cell; suppressed ("<5") or missing cells count as 0 (G4 B3 B-2)."""
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def is_additive(compiled: CompiledQuery) -> bool:
    """Only count/sum results may be added across groups (an average of averages is not a fact)."""
    return compiled.aggregation in ("count", "sum") and compiled.unit not in (
        "pct", "usd_per_boe", "inr_per_boe", "ratio", "score")


def fmt_num(v: Any, unit: str = "") -> str:
    """Indian-style number formatting for speech/display (₹ crore keeps 2 decimals max)."""
    if isinstance(v, bool) or v is None:
        return str(v)
    try:
        x = float(v)
    except (TypeError, ValueError):
        return str(v)
    if unit in ("pct",):
        return f"{x:.1f}%"
    if x < 0 and unit in ("usd_per_boe", "inr_cr", "inr_lakh"):
        return "−" + fmt_num(-x, unit)
    if unit in ("usd_per_boe",):
        return f"${x:,.2f}"
    if unit == "inr_per_boe":
        return f"₹{x:,.0f}/BOE"
    if abs(x - round(x)) < 1e-9 and abs(x) >= 1:
        s = f"{int(round(x)):,}"
    else:
        s = f"{x:,.2f}".rstrip("0").rstrip(".")
    if unit == "inr_cr":
        return f"₹{s} crore"
    if unit == "inr_lakh":
        return f"₹{s} lakh"
    return s


def localise_rows(compiled: CompiledQuery, result: QueryResult) -> Tuple[List[str], List[Dict[str, Any]], Dict[str, Dict[str, str]]]:
    """Entity codes -> names in dimension columns; returns (columns, rows, name->code maps)."""
    ents = get_entities()
    codes: Dict[str, Dict[str, str]] = {}
    rows = []
    for r in result.rows:
        r2 = {k: v for k, v in r.items() if k != "_total_rows"}
        for col, etype in compiled.entity_columns.items():
            code = r2.get(col)
            if isinstance(code, str):
                name = ents.friendly(code) if etype != "grade" else code
                codes.setdefault(col, {})[name] = code
                r2[col] = name
        rows.append(r2)
    return [c for c in result.columns if c != "_total_rows"], rows, codes


def total_rows(result: QueryResult) -> int:
    """Exact number of matching rows (window count) even when the row list is capped."""
    if result.rows and "_total_rows" in result.rows[0]:
        return int(result.rows[0]["_total_rows"])
    return len(result.rows)


def scope_phrases(spec: QuerySpec, compiled: Optional[CompiledQuery] = None) -> List[str]:
    """Human scope of the question, e.g. ['Delhi HQ', 'Executives', 'Station stay ≥ 5 yrs', 'FY26']."""
    ents = get_entities()
    out: List[str] = []
    for f in spec.filters:
        vals = f.value if isinstance(f.value, list) else [f.value]
        if f.field in ("wc", "asset"):
            names = [ents.wc_name(str(v)) for v in vals]
            out.append(" vs ".join(names) if f.op == "in" and spec.is_compare() else ", ".join(names))
        elif f.field == "discipline":
            out.append(", ".join(ents.friendly(str(v)) for v in vals))
        elif f.field == "field":
            out.append(", ".join(ents.friendly(str(v)) for v in vals))
        elif f.field == "cadre":
            out.append(", ".join(str(v).replace("_", "-").title() + "s" for v in vals))
        elif f.field == "grade":
            sym = {">=": " and above", ">": " and above (excl.)", "<=": " and below", "<": " and below (excl.)"}.get(f.op, "")
            out.append(f"{', '.join(map(str, vals))}{sym}")
        elif f.field == "station_tenure_years":
            out.append(f"Station stay {f.op} {vals[0]} yrs")
        elif f.field == "region":
            out.append(", ".join(str(v).title() for v in vals))
        else:
            out.append(f"{f.field.replace('_', ' ')} {f.op} {', '.join(map(str, vals))}")
    p = (compiled.effective_period if compiled else {}) or {}
    if p.get("fy"):
        out.append(p["fy"] + (" YTD" if p["fy"] == "FY27" else ""))
    elif p.get("from"):
        out.append(f"{p['from']}–{p['to']}")
    elif p.get("as_of"):
        out.append("As of 19-Oct-2026")
    return out


def build_visual(spec: QuerySpec, compiled: CompiledQuery, columns: List[str], rows: List[Dict[str, Any]],
                 chart_kind: Optional[str], title: str, subtitle: str, mode: str,
                 n_total: Optional[int] = None) -> Dict[str, Any]:
    unit = CHART_UNIT.get(compiled.unit)
    cap = 2000 if compiled.grain == "row" else 200   # rosters ship whole (UI virtualises, U5.2)
    table = {"columns": columns, "rows": rows[:cap], "total_rows": n_total if n_total is not None else len(rows)}
    vis: Dict[str, Any] = {"type": "table", "mode": mode, "title": title, "subtitle": subtitle, "table": table}
    if compiled.grain == "row" or not rows:
        return vis
    dims = [alias for _, alias in compiled.dims]
    val = compiled.value_columns[0] if compiled.value_columns else (columns[-1] if columns else None)
    if not dims:
        r0 = rows[0]
        vis["type"] = "kpi"
        vis["kpis"] = [{"label": compiled.metric_label if c == compiled.metric else c.replace("_", " ").title(),
                        "value": r0.get(c), "unit": UNIT_WORDS.get(compiled.unit, "") if c == compiled.metric else ""}
                       for c in compiled.value_columns if c in r0]
        return vis
    cmp = spec.is_compare()
    if cmp and len(dims) >= 1:
        lead = dims[0]
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows:
            groups.setdefault(str(r.get(lead)), []).append(r)
        items = []
        for label, grp in groups.items():
            total = sum(_num(g.get(val)) for g in grp) if is_additive(compiled) else (
                grp[0].get(val) if len(grp) == 1 else None)
            item: Dict[str, Any] = {"label": label, "kpis": []}
            if total is not None:
                item["kpis"].append({"label": compiled.metric_label, "value": round(_num(total), 2) if not isinstance(total, str) else total,
                                     "unit": UNIT_WORDS.get(compiled.unit, "")})
            if len(dims) > 1:
                item["chart"] = build_chart_spec(kind="hbar", columns=[dims[1], val], rows=grp, title=label, unit=unit)
            items.append(item)
        if 2 <= len(items) <= 4:
            vis["compare"] = {"items": items, "metric": compiled.metric_label, "shared_axis": True}
            vis["mode"] = "compare"
        kind = chart_kind or ("grouped_bar" if len(dims) > 1 else "bar")
        if kind != "table":
            vis["type"] = "chart"
            cols_for_chart = [dims[1], val, lead] if len(dims) > 1 else [lead, val]
            chart = build_chart_spec(kind=kind, columns=cols_for_chart, rows=rows, title=title, unit=unit)
            if len(dims) > 1:
                chart.update({"x": dims[1], "category": dims[1], "series": lead, "y": val, "value": val})
            vis["chart"] = chart
        return vis
    if compiled.unit in ("pct", "usd_per_boe", "ratio") and len(compiled.value_columns) > 1:
        pass  # mixed measures still chart the primary measure only
    kind = chart_kind or ("line" if dims[0] == "fiscal_year" else select_chart_kind(columns=[dims[0], val], rows=rows))
    if kind == "kpi":
        kind = "bar"
    if kind != "table":
        vis["type"] = "chart"
        vis["chart"] = build_chart_spec(kind=kind, columns=[dims[0], val] + [c for c in compiled.value_columns[1:2]],
                                        rows=rows, title=title, unit=unit)
    return vis


def narrate(spec: QuerySpec, compiled: CompiledQuery, columns: List[str], rows: List[Dict[str, Any]],
            n_total: Optional[int] = None) -> str:
    """2–4 sentence spoken answer built only from result values."""
    scope = ", ".join(scope_phrases(spec, compiled))
    unit_word = UNIT_WORDS.get(compiled.unit, "")
    if not rows:
        return f"No records match {scope or 'this question'} in the data. Try widening a filter."
    if compiled.grain == "row":
        noun = "people" if compiled.subject == "workforce" else "rows"
        first = rows[0]
        n = n_total if n_total is not None else len(rows)
        lead = f"{n:,} {noun} match ({scope})." if scope else f"{n:,} {noun} match."
        if n > len(rows):
            lead += f" Showing the first {len(rows):,}."
        sorted_by_stay = (not spec.sort) or (spec.sort.by == "station_tenure_years" and spec.sort.dir == "desc")
        if compiled.subject == "workforce" and first.get("name") and sorted_by_stay:
            lead += (f" The longest station stay is {first.get('name')}, {first.get('designation') or first.get('grade')}, "
                     f"at {fmt_num(first.get('station_tenure_years'))} years.")
        elif compiled.subject == "mou":
            weakest = min(rows, key=lambda r: float(r.get("pct_of_excellent") or 0))
            lead = (f"{len(rows)} MoU parameters ({scope}). Weakest against the Excellent target: "
                    f"{weakest.get('parameter')} at {fmt_num(weakest.get('pct_of_excellent'), 'pct')} of target.")
        return lead + " The full list is on screen."
    dims = [alias for _, alias in compiled.dims]
    val = compiled.value_columns[0] if compiled.value_columns else None
    if not dims and val:
        v = rows[0].get(val)
        s = f"{compiled.metric_label}: {fmt_num(v, compiled.unit)}" + (f" {unit_word}" if unit_word and compiled.unit not in ("inr_cr", "inr_lakh", "pct", "usd_per_boe") else "")
        return s + (f" ({scope})." if scope else ".") + " Details are on screen."
    additive = is_additive(compiled)
    cmp = spec.is_compare()
    if cmp:
        lead = dims[0]
        totals: Dict[str, float] = {}
        counts: Dict[str, int] = {}
        for r in rows:
            k = str(r.get(lead))
            counts[k] = counts.get(k, 0) + 1
            totals[k] = totals.get(k, 0.0) + _num(r.get(val))
        if not additive and any(c > 1 for c in counts.values()):
            # averages/ratios split by a second dimension: name each group's highest value instead of a sum
            best: Dict[str, Dict[str, Any]] = {}
            for r in rows:
                k = str(r.get(lead))
                if k not in best or _num(r.get(val)) > _num(best[k].get(val)):
                    best[k] = r
            parts = [f"{k}: highest {b.get(dims[1])} ({fmt_num(b.get(val), compiled.unit)})" for k, b in best.items()]
            return f"{compiled.metric_label} — " + "; ".join(parts) + ". Details are on screen."
        parts = [f"{k}: {fmt_num(v, compiled.unit)}" for k, v in totals.items()]
        others = [s for s in scope_phrases(spec, compiled) if " vs " not in s]
        s = f"{compiled.metric_label} — " + " vs ".join(parts) + (f" ({', '.join(others)})." if others else ".")
        if len(dims) > 1:
            top = max(rows, key=lambda r: _num(r.get(val)))
            s += f" The largest single group is {top.get(dims[1])} in {top.get(lead)} ({fmt_num(top.get(val), compiled.unit)})."
        return s + " Details are on screen."
    dim = dims[0]
    rows = [r for r in rows if isinstance(r.get(val), (int, float)) and not isinstance(r.get(val), bool)]
    if not rows:
        return f"No {compiled.metric_label.lower()} values are recorded for {scope or 'this selection'}."
    if len(dims) > 1 and additive:
        # several breakdowns: rank the first one by its total so names are not repeated
        agg: Dict[Any, float] = {}
        for r in rows:
            agg[r.get(dim)] = agg.get(r.get(dim), 0.0) + _num(r.get(val))
        rows = [{dim: k, val: v} for k, v in agg.items()]
    ranked = sorted(rows, key=lambda r: _num(r.get(val)), reverse=True)
    plural = DIM_PLURAL.get(dim, "groups")
    if dim == "fiscal_year":
        first, last = rows[0], rows[-1]
        return (f"{compiled.metric_label} moved from {fmt_num(first.get(val), compiled.unit)} in {first.get(dim)} to "
                f"{fmt_num(last.get(val), compiled.unit)} in {last.get(dim)}" + (f" ({scope})." if scope else ".")
                + " The trend is on screen.")
    s = ""
    if additive:
        total = sum(_num(r.get(val)) for r in rows)
        s = f"{fmt_num(total, compiled.unit)}" + (f" {unit_word}" if unit_word and compiled.unit not in ("inr_cr", "inr_lakh") else "") + f" across {len(rows)} {plural}"
        s += f" ({scope}). " if scope else ". "
    top = ranked[:2]
    s += "Highest: " + " and ".join(f"{r.get(dim)} ({fmt_num(r.get(val), compiled.unit)})" for r in top) + "."
    neg = [r for r in rows if isinstance(r.get(val), (int, float)) and r.get(val) < 0]
    if "change" in (val or ""):
        flat = [r for r in rows if _num(r.get(val)) <= 0]
        s += f" {len(flat)} of {len(rows)} {plural} saw no increase."
        neg = []
    if neg:
        s += f" {len(neg)} {'is' if len(neg) == 1 else 'are'} negative: " + ", ".join(
            f"{r.get(dim)} ({fmt_num(r.get(val), compiled.unit)})" for r in sorted(neg, key=lambda r: r.get(val))[:3]) + "."
    elif len(ranked) > 2:
        low = ranked[-1]
        s += f" Lowest: {low.get(dim)} ({fmt_num(low.get(val), compiled.unit)})."
    return s + " Details are on screen."


def context_chips(spec: QuerySpec, compiled: CompiledQuery, persona: str) -> List[Dict[str, str]]:
    chips = [{"label": persona, "kind": "role"}]
    for s in scope_phrases(spec, compiled)[:4]:
        kind = "period" if (s.startswith("FY") or s.startswith("As of")) else "filter"
        chips.append({"label": s, "kind": kind})
    chips.append({"label": "Source: " + ", ".join(t.split(".")[-1] for t in compiled.tables), "kind": "source"})
    return chips[:6]
