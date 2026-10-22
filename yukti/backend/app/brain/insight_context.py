"""Glue between query results and the insight library (B4).

- `build_insight_context`: result rows + compiled query -> InsightContext (incl. targets such as
  sanctioned posts, and the previous-FY rows for the delta insight).
- `previous_period_spec`: the same spec one FY earlier (only for single-FY fiscal-year subjects).
- `derived_numbers`: totals / per-group aggregates the presenter states, so the grounding check
  accepts them (they are computed from the rows, never invented).
- `table_insights`: insights for legacy-path tables (no QuerySpec), so every data answer carries them.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.brain.compiler import CompiledQuery
from app.brain.insights import ADDITIVE_UNITS, InsightContext, compute_insights
from app.brain.query_spec import Period, QuerySpec, SpecPatch, apply_patch
from app.brain.semantic_model import get_semantic_model


def previous_period_spec(spec: QuerySpec, compiled: CompiledQuery) -> Optional[QuerySpec]:
    if compiled.subject is None or compiled.grain != "aggregate":
        return None
    subject = get_semantic_model().subjects.get(compiled.subject)
    if subject is None or subject.period != "fiscal_year" or "fy" in spec.dimensions:
        return None
    fy = (compiled.effective_period or {}).get("fy")
    if not fy:
        return None
    prev = f"FY{int(fy[2:]) - 1:02d}"
    return apply_patch(spec, SpecPatch(period=Period(fy=prev)))


def build_insight_context(spec: QuerySpec, compiled: CompiledQuery, rows: List[Dict[str, Any]], n_total: int,
                          prev_rows: Optional[List[Dict[str, Any]]], scope: List[str]) -> InsightContext:
    dims = [alias for _, alias in compiled.dims]
    # Prefer the first dimension with >= 2 distinct values in rows so filtered multi-dim queries
    # (e.g. single asset across multiple FYs) compute insights across the varying dimension.
    chosen_dim = dims[0] if dims else None
    if rows and len(dims) > 1:
        for d in dims:
            if len({r.get(d) for r in rows if r.get(d) is not None}) >= 2:
                chosen_dim = d
                break
    value_col = compiled.value_columns[0] if compiled.value_columns else None
    unit = compiled.unit if compiled.aggregation in ("count", "sum") or compiled.unit not in ADDITIVE_UNITS else "ratio"
    metric = get_semantic_model().metrics.get(compiled.metric)
    ctx = InsightContext(
        metric=compiled.metric, metric_label=compiled.metric_label, unit=unit,
        dim=chosen_dim, value_col=value_col, rows=rows, n_total=n_total,
        subject=compiled.subject, grain=compiled.grain, scope=scope,
        polarity=getattr(metric, "polarity", None) if metric else None,
    )
    if prev_rows is not None:
        fy = (compiled.effective_period or {}).get("fy")
        ctx.prev_rows = prev_rows
        ctx.prev_label = f"FY{int(fy[2:]) - 1:02d}" if fy else "last year"
    # Targets: in-position vs sanctioned for posts; achievement vs Excellent target for MoU rows.
    if rows and dims and "sanctioned_posts" in rows[0] and "in_position" in rows[0]:
        ctx.value_col = "in_position"
        ctx.unit = "employees"
        ctx.targets = {r.get(dims[0]): float(r["sanctioned_posts"]) for r in rows
                       if isinstance(r.get("sanctioned_posts"), (int, float))}
        ctx.target_label = "sanctioned strength"
    if compiled.subject == "mou" and rows and "excellent_target" in rows[0]:
        ctx.dim, ctx.value_col, ctx.unit = "parameter", "pct_of_excellent", "pct"
        ctx.targets = {r.get("parameter"): 100.0 for r in rows}
        ctx.target_label = "Excellent target (100%)"
    if compiled.metric == "capex_vs_reserves" and rows:
        ctx.dim, ctx.value_col, ctx.unit = "asset", "capex_cr", "inr_cr"
        ctx.extra_insights = _under_investment(rows)
    if compiled.metric == "headcount_change" and rows:
        ctx.dim, ctx.value_col, ctx.unit = "work_centre", "headcount_change", "employees"
    return ctx


def _under_investment(rows: List[Dict[str, Any]]):
    """C7 logic: assets whose capex per MMTOE of 2P reserves is below half the average."""
    from app.brain.insights import Insight, fmt
    flagged = [r for r in rows if r.get("under_invested") is True]
    avg = next((r.get("avg_capex_cr_per_mmtoe") for r in rows if isinstance(r.get("avg_capex_cr_per_mmtoe"), (int, float))), None)
    if not flagged or avg is None:
        return []
    flagged.sort(key=lambda r: float(r.get("reserves_2p_mmtoe") or 0), reverse=True)
    names = ", ".join(f"{r.get('asset')} (₹{fmt(float(r.get('capex_cr_per_mmtoe') or 0))} cr per MMTOE)" for r in flagged[:3])
    facts = [float(avg), float(len(flagged))] + [float(r.get("capex_cr_per_mmtoe") or 0) for r in flagged[:3]]
    return [Insight(kind="risk", type="named_exception", value=len(flagged), unit="assets", ref=flagged[0].get("asset"),
                    text=f"{len(flagged)} asset{'s are' if len(flagged) != 1 else ' is'} under-invested relative to 2P reserves "
                         f"(below half the ₹{fmt(float(avg))} cr per MMTOE average): {names}.",
                    facts=facts, priority=5)]


def derived_numbers(compiled: CompiledQuery, rows: List[Dict[str, Any]], n_total: int) -> List[float]:
    out: List[float] = [float(n_total), float(len(rows))]
    dims = [alias for _, alias in compiled.dims]
    for col in compiled.value_columns:
        vals = [float(r[col]) for r in rows if isinstance(r.get(col), (int, float)) and not isinstance(r.get(col), bool)]
        if vals:
            out += [round(sum(vals), 2), round(sum(vals)), len(vals)]
        if dims:
            agg: Dict[Any, float] = {}
            for r in rows:
                v = r.get(col)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    agg[r.get(dims[0])] = agg.get(r.get(dims[0]), 0.0) + float(v)
            out += [round(v, 2) for v in agg.values()]
            out.append(float(len(agg)))
    return out


def table_insights(columns: List[str], rows: List[Any], max_n: int = 4):
    """Generic insights for a legacy table: first text column = dimension, first count/amount column = value."""
    if not rows or not columns:
        return []
    norm_rows: List[Dict[str, Any]] = []
    for r in rows:
        if isinstance(r, dict):
            d = dict(r)
        elif isinstance(r, (list, tuple)):
            d = {c: v for c, v in zip(columns, r)}
        else:
            continue
        for k, v in list(d.items()):
            if isinstance(v, bool) or v is None:
                continue
            if not isinstance(v, (int, float)):
                try:
                    d[k] = float(v)
                except (ValueError, TypeError):
                    pass
        norm_rows.append(d)
    if not norm_rows:
        return []
    def numeric(c):
        return all(isinstance(r.get(c), (int, float)) and not isinstance(r.get(c), bool) for r in norm_rows[:20] if r.get(c) is not None) \
            and any(isinstance(r.get(c), (int, float)) for r in norm_rows[:20])
    dims = [c for c in columns if not numeric(c)]
    vals = [c for c in columns if numeric(c) and not c.endswith("_id")]
    if not vals:
        return []
    if not dims or len(norm_rows) == 1:
        ctx1 = InsightContext(metric=vals[0], metric_label=vals[0].replace("_", " ").capitalize(), unit="",
                              dim=None, value_col=vals[0], rows=norm_rows[:1], n_total=len(norm_rows))
        return compute_insights(ctx1, max_n=max_n)
    chosen_dim = dims[0]
    for d in dims:
        if len({r.get(d) for r in norm_rows if r.get(d) is not None}) >= 2:
            chosen_dim = d
            break
    preferred = [c for c in vals if any(k in c.lower() for k in ("count", "headcount", "employees", "executives", "vacanc",
                                                                   "posts", "_cr", "revenue", "pbt", "ebitda", "cost"))]
    val = (preferred or vals)[0]
    additive = not any(k in val.lower() for k in ("pct", "rate", "ratio", "avg", "per_", "margin", "share", "score"))
    unit = "inr_cr" if val.lower().endswith("_cr") and additive else ("employees" if additive else "ratio")
    ctx = InsightContext(metric=val, metric_label=val.replace("_", " ").title(), unit=unit, dim=chosen_dim,
                         value_col=val, rows=norm_rows, n_total=len(norm_rows))
    return compute_insights(ctx, max_n=max_n)
