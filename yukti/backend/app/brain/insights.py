"""Deterministic insight library (B4.1, FEAT-011).

Every insight is computed in Python from the query result (never by the LLM) and carries
the numbers it used (`facts`) so the narrator's numeric-grounding check can verify them.
Contract mapping: `Insight.to_contract()` -> contract-v2 `insights_v2[]` item
`{text, kind, value, unit, ref}` with kind in headline|trend|outlier|risk|comparison|note.

Reference implementations (Opus): `share_of_total`, `rank_extremes`.
Remaining types (Flash, packet B4.1): `delta_vs_last_year`, `vs_target`, `outliers`,
`concentration`, `named_exceptions`, `policy_flags`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Callable, Dict, List, Optional

UNIT_SUFFIX = {"pct": "%", "usd_per_boe": " $/BOE", "inr_cr": " ₹ cr", "employees": "", "posts": "", "years": " yrs"}
ADDITIVE_UNITS = {"employees", "posts", "workers", "inr_cr", "inr_lakh", "boe", "mmtoe", "incidents", "parameters"}


@dataclass
class Insight:
    kind: str                      # headline | trend | outlier | risk | comparison | note
    text: str
    value: Optional[float] = None
    unit: str = ""
    ref: Optional[str] = None      # row / category the insight refers to (UI highlight)
    facts: List[float] = field(default_factory=list)
    type: str = ""                 # library type (share, rank, delta, vs_target, outlier, concentration, ...)
    priority: int = 50             # lower = more important

    def to_contract(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"text": self.text, "kind": self.kind}
        if self.value is not None:
            d["value"] = round(self.value, 2) if isinstance(self.value, float) else self.value
        if self.unit:
            d["unit"] = self.unit
        if self.ref is not None:
            d["ref"] = str(self.ref)
        return d


@dataclass
class InsightContext:
    """Everything an insight function may look at. Rows are already localised (names, not codes)."""

    metric: str
    metric_label: str
    unit: str
    dim: Optional[str]                         # first breakdown column (output alias), None for a single value
    value_col: Optional[str]
    rows: List[Dict[str, Any]]
    n_total: int = 0
    subject: Optional[str] = None
    grain: str = "aggregate"
    scope: List[str] = field(default_factory=list)
    prev_rows: Optional[List[Dict[str, Any]]] = None    # same query for the previous FY (delta_vs_last_year)
    prev_label: Optional[str] = None                    # e.g. "FY25"
    targets: Optional[Dict[str, float]] = None          # category -> target/sanctioned value (vs_target)
    target_label: str = "target"
    polarity: Optional[str] = None                      # "higher" | "lower" is better (risk wording)
    extra_insights: List["Insight"] = field(default_factory=list)  # analysis-specific insights (e.g. C7 under-investment)


def fmt(v: float, unit: str = "") -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "n/a"
    if v < 0 and unit in ("inr_cr", "usd_per_boe"):
        return "−" + fmt(-v, unit)
    if unit == "pct":
        return f"{v:.1f}%"
    if unit == "usd_per_boe":
        return f"${v:,.2f}"
    if unit == "inr_cr":
        return f"₹{v:,.2f} cr".replace(".00 cr", " cr")
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v)):,}"
    return f"{v:,.2f}"


def numeric_rows(ctx: InsightContext) -> List[Dict[str, Any]]:
    if not ctx.value_col:
        return []
    return [r for r in ctx.rows if isinstance(r.get(ctx.value_col), (int, float)) and not isinstance(r.get(ctx.value_col), bool)]


def aggregate_by_dim(ctx: InsightContext) -> Dict[Any, float]:
    out: Dict[Any, float] = {}
    for r in numeric_rows(ctx):
        out[r.get(ctx.dim)] = out.get(r.get(ctx.dim), 0.0) + float(r[ctx.value_col])
    return out


# ------------------------------------------------------------------ reference types (Opus)
def share_of_total(ctx: InsightContext) -> Optional[Insight]:
    """Largest category's share of an additive total (e.g. 'Finance & Accounts is 23.6% of 419')."""
    if not ctx.dim or ctx.unit not in ADDITIVE_UNITS:
        return None
    if ctx.dim in ("fy", "fiscal_year"):
        return None
    agg = aggregate_by_dim(ctx)
    total = sum(agg.values())
    if len(agg) < 2 or total <= 0:
        return None
    top, v = max(agg.items(), key=lambda kv: kv[1])
    share = 100.0 * v / total
    return Insight(kind="headline", type="share", value=round(share, 1), unit="%", ref=top,
                   text=f"{top} accounts for {share:.1f}% of the total ({fmt(v, ctx.unit)} of {fmt(total, ctx.unit)}).",
                   facts=[round(share, 1), v, total], priority=10)


def rank_extremes(ctx: InsightContext) -> Optional[Insight]:
    """Top and bottom of the ranking with the gap between them."""
    if not ctx.dim:
        return None
    agg = aggregate_by_dim(ctx) if ctx.unit in ADDITIVE_UNITS else {
        r.get(ctx.dim): float(r[ctx.value_col]) for r in numeric_rows(ctx)}
    if len(agg) < 3:
        return None
    ranked = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)
    (hi, hv), (lo, lv) = ranked[0], ranked[-1]
    return Insight(kind="comparison", type="rank", value=hv, unit=ctx.unit, ref=hi,
                   text=f"Highest is {hi} ({fmt(hv, ctx.unit)}); lowest is {lo} ({fmt(lv, ctx.unit)}) across {len(ranked)} groups.",
                   facts=[hv, lv, float(len(ranked))], priority=20)


# ------------------------------------------------------------------ remaining types (packet B4.1)
def _is_ge_5(v: Any) -> bool:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v >= 5
    if isinstance(v, str):
        try:
            return float(v) >= 5
        except ValueError:
            return False
    return False


def _is_exempt(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.lower() in ("true", "1", "yes")
    return False


def delta_vs_last_year(ctx: InsightContext) -> Optional[Insight]:
    if ctx.prev_rows is None or not ctx.prev_label or not ctx.value_col:
        return None
    curr_rows = numeric_rows(ctx)
    prev_rows = [
        r for r in ctx.prev_rows
        if isinstance(r.get(ctx.value_col), (int, float)) and not isinstance(r.get(ctx.value_col), bool)
    ]
    if not curr_rows or not prev_rows:
        return None
    if ctx.unit in ADDITIVE_UNITS:
        curr_total = sum(float(r[ctx.value_col]) for r in curr_rows)
        prev_total = sum(float(r[ctx.value_col]) for r in prev_rows)
    else:
        if len(curr_rows) != 1 or len(prev_rows) != 1:
            return None
        curr_total = float(curr_rows[0][ctx.value_col])
        prev_total = float(prev_rows[0][ctx.value_col])

    if prev_total == 0 or math.isnan(prev_total) or math.isnan(curr_total):
        return None

    diff = curr_total - prev_total
    abs_change = abs(diff)
    pct = 100.0 * diff / prev_total

    if abs_change < 1e-9:
        text = f"{ctx.metric_label} is unchanged vs {ctx.prev_label}."
        return Insight(
            kind="trend",
            type="delta",
            value=0.0,
            unit="%",
            ref=None,
            text=text,
            facts=[0.0],
            priority=15,
        )

    direction = "up" if diff > 0 else "down"
    change_str = fmt(abs_change, ctx.unit)
    text = f"{ctx.metric_label} is {direction} {change_str} ({pct:+.1f}%) vs {ctx.prev_label}."
    facts = [abs_change, round(pct, 1)]
    return Insight(
        kind="trend",
        type="delta",
        value=round(pct, 1),
        unit="%",
        ref=None,
        text=text,
        facts=facts,
        priority=15,
    )


def vs_target(ctx: InsightContext) -> Optional[Insight]:
    if not ctx.targets or not ctx.dim or not ctx.value_col:
        return None
    agg = aggregate_by_dim(ctx) if ctx.unit in ADDITIVE_UNITS else {
        r.get(ctx.dim): float(r[ctx.value_col]) for r in numeric_rows(ctx)
    }
    common = [c for c in agg if c in ctx.targets]
    if not common:
        return None

    target_label = ctx.target_label or "target"
    misses = []
    for c in common:
        actual = agg[c]
        target = float(ctx.targets[c])
        gap = actual - target
        if gap < 0:
            misses.append((c, actual, target, -gap))

    if not misses:
        n = len(common)
        text = f"All {n} categories meet the {target_label}."
        return Insight(
            kind="comparison",
            type="vs_target",
            value=float(n),
            unit="",
            ref=None,
            text=text,
            facts=[float(n)],
            priority=12,
        )

    worst = max(misses, key=lambda item: item[3])
    cat, actual, target, shortfall = worst
    text = (
        f"{cat} is {fmt(shortfall, ctx.unit)} below {target_label} "
        f"({fmt(actual, ctx.unit)} vs {fmt(target, ctx.unit)})."
    )
    facts = [shortfall, actual, target]
    return Insight(
        kind="risk",
        type="vs_target",
        value=round(-shortfall, 2),
        unit=ctx.unit,
        ref=str(cat),
        text=text,
        facts=facts,
        priority=12,
    )


def outliers(ctx: InsightContext) -> Optional[Insight]:
    if not ctx.dim or not ctx.value_col:
        return None
    agg = aggregate_by_dim(ctx) if ctx.unit in ADDITIVE_UNITS else {
        r.get(ctx.dim): float(r[ctx.value_col]) for r in numeric_rows(ctx)
    }
    if len(agg) < 5:
        return None

    import statistics
    vals = list(agg.values())
    med = float(statistics.median(vals))
    devs = [abs(x - med) for x in vals]
    mad = float(statistics.median(devs))
    if mad == 0 or math.isnan(mad):
        return None

    flagged = []
    for cat, x in agg.items():
        z = 0.6745 * (x - med) / mad
        if abs(z) > 3.5:
            flagged.append((cat, x, z, abs(z)))

    if not flagged:
        return None

    cat, x, z, _ = max(flagged, key=lambda item: item[3])
    text = f"{cat} is an outlier at {fmt(x, ctx.unit)} (median {fmt(med, ctx.unit)})."
    facts = [x, med]
    return Insight(
        kind="outlier",
        type="outlier",
        value=x,
        unit=ctx.unit,
        ref=str(cat),
        text=text,
        facts=facts,
        priority=25,
    )


def concentration(ctx: InsightContext) -> Optional[Insight]:
    if not ctx.dim or not ctx.value_col or ctx.unit not in ADDITIVE_UNITS:
        return None
    if ctx.dim in ("fy", "fiscal_year"):
        return None
    agg = aggregate_by_dim(ctx)
    if len(agg) < 4:
        return None
    total = sum(agg.values())
    if total <= 0:
        return None

    ranked = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)
    top3 = ranked[:3]
    top3_sum = sum(v for _, v in top3)
    share = 100.0 * top3_sum / total
    if share < 50.0:
        return None

    a, b, c = top3[0][0], top3[1][0], top3[2][0]
    text = f"The top 3 ({a}, {b}, {c}) hold {share:.1f}% of the total."
    facts = [round(share, 1), 3.0]
    return Insight(
        kind="note",
        type="concentration",
        value=round(share, 1),
        unit="%",
        ref=None,
        text=text,
        facts=facts,
        priority=30,
    )


def named_exceptions(ctx: InsightContext) -> Optional[Insight]:
    if not ctx.value_col:
        return None
    if ctx.dim:
        agg = aggregate_by_dim(ctx) if ctx.unit in ADDITIVE_UNITS else {
            r.get(ctx.dim): float(r[ctx.value_col]) for r in numeric_rows(ctx)
        }
        items = list(agg.items())
    else:
        items = [(r.get("name") or "row", float(r[ctx.value_col])) for r in numeric_rows(ctx)]

    negatives = [(cat, v) for cat, v in items if v < 0]
    if not negatives:
        return None

    k = len(negatives)
    negatives.sort(key=lambda kv: kv[1])
    top = negatives[:3]

    parts = [f"{cat} ({fmt(v, ctx.unit)})" for cat, v in top]
    joined = ", ".join(parts)
    if k == 1:
        text = f"1 is negative: {joined}."
    else:
        text = f"{k} negative: {joined}."

    facts = [float(k)] + [v for _, v in top]
    return Insight(
        kind="risk",
        type="named_exception",
        value=top[0][1],
        unit=ctx.unit,
        ref=str(top[0][0]),
        text=text,
        facts=facts,
        priority=18,
    )


def policy_flags(ctx: InsightContext) -> Optional[Insight]:
    if ctx.grain != "row" or not ctx.rows:
        return None
    if not any("station_tenure_years" in r for r in ctx.rows):
        return None

    n = len(ctx.rows)
    due = sum(1 for r in ctx.rows if _is_ge_5(r.get("station_tenure_years")))
    exempt = sum(1 for r in ctx.rows if _is_exempt(r.get("retiring_within_3yr")))

    text = f"{due} of {n} are past the 5-year rotation norm; {exempt} are within 3 years of superannuation (exempt)."
    facts = [float(due), float(n), 5.0, float(exempt), 3.0]
    return Insight(
        kind="risk",
        type="policy_flag",
        value=float(due),
        unit="employees",
        ref=None,
        text=text,
        facts=facts,
        priority=16,
    )


# ------------------------------------------------------------------ coverage types (Opus, B4 gate)
def headline_values(ctx: InsightContext) -> Optional[List[Insight]]:
    """Single-row answers (KPI or 1-row group): state up to two measured values with their labels."""
    if len(ctx.rows) != 1 or ctx.grain == "row":
        return None
    r = ctx.rows[0]
    out: List[Insight] = []
    for k, v in r.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool) and not k.startswith("_"):
            label = ctx.metric_label if k == ctx.value_col else k.replace("_", " ").capitalize()
            unit = ctx.unit if k == ctx.value_col else ""
            scope = f" ({', '.join(ctx.scope)})" if ctx.scope and not out else ""
            out.append(Insight(kind="headline", type="headline", value=float(v), unit=unit, ref=None,
                               text=f"{label}: {fmt(float(v), unit)}{scope}.", facts=[float(v)], priority=9 + len(out)))
        if len(out) == 2:
            break
    return out or None


def roster_mix(ctx: InsightContext) -> Optional[List[Insight]]:
    """Roster answers: the largest grade and discipline groups among the listed people."""
    if ctx.grain != "row" or not ctx.rows:
        return None
    out: List[Insight] = []
    n = len(ctx.rows)
    for col, noun in (("grade", "grade"), ("discipline", "discipline")):
        counts: Dict[Any, int] = {}
        for r in ctx.rows:
            if r.get(col) is not None:
                counts[r.get(col)] = counts.get(r.get(col), 0) + 1
        if len(counts) >= 2:
            top, c = max(counts.items(), key=lambda kv: kv[1])
            out.append(Insight(kind="note", type="roster_mix", value=c, unit="employees", ref=top,
                               text=f"The largest {noun} group is {top}: {c} of {n} ({100.0 * c / n:.1f}%).",
                               facts=[float(c), float(n), round(100.0 * c / n, 1)], priority=21 + len(out)))
    return out or None


def top_two_gap(ctx: InsightContext):
    """Two-way comparisons and non-additive measures: the leader and its gap to the runner-up."""
    if not ctx.dim:
        return None
    if ctx.unit in ADDITIVE_UNITS:
        agg = aggregate_by_dim(ctx)
    else:
        agg = {r.get(ctx.dim): float(r[ctx.value_col]) for r in numeric_rows(ctx)}
    if len(agg) < 2 or (ctx.unit in ADDITIVE_UNITS and len(agg) >= 3):
        return None  # additive rankings of 3+ are covered by share/rank
    (a, av), (b, bv) = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)[:2]
    gap = av - bv
    gap_ins = Insight(kind="comparison", type="gap", value=round(gap, 2), unit=ctx.unit, ref=a,
                      text=f"{a} leads {b} by {f'{gap:.1f} pts' if ctx.unit == 'pct' else fmt(gap, ctx.unit)} "
                           f"({fmt(av, ctx.unit)} vs {fmt(bv, ctx.unit)}).",
                      facts=[round(gap, 2), av, bv], priority=22)
    if len(agg) == 2 and ctx.unit not in ADDITIVE_UNITS:
        head_ins = Insight(kind="headline", type="rank", value=av, unit=ctx.unit, ref=a,
                           text=f"Highest is {a} at {fmt(av, ctx.unit)}; lowest is {b} at {fmt(bv, ctx.unit)}.",
                           facts=[av, bv], priority=11)
        return [head_ins, gap_ins]
    return gap_ins


INSIGHT_FUNCS: List[Callable[[InsightContext], Optional[Insight]]] = [
    headline_values, roster_mix, top_two_gap,
    share_of_total, rank_extremes, delta_vs_last_year, vs_target, outliers, concentration,
    named_exceptions, policy_flags,
]


def compute_insights(ctx: InsightContext, max_n: int = 4) -> List[Insight]:
    """Runs every insight type; returns up to `max_n` by priority (stable, deterministic)."""
    out: List[Insight] = list(ctx.extra_insights or [])
    for fn in INSIGHT_FUNCS:
        try:
            res = fn(ctx)
        except Exception:  # an insight must never break an answer
            res = None
        if res is None:
            continue
        out.extend(res if isinstance(res, list) else [res])
    out.sort(key=lambda i: i.priority)
    return out[:max_n]
