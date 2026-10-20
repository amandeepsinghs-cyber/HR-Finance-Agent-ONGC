"""Chart Selection Rules and Declarative ECharts Spec Generator.
Implements the UX Spec §6 rules to determine the optimal visualization
and output a declarative chart_spec conforming to answer_contract.schema.json.
Enforces:
- C1: Donut by grade (or grade bars), never stacking overlapping totals and components.
- Accurate units: headcount/count gets 'executives' or 'count' (never '₹ Crore').
- Category limits: <= 12 categories, otherwise top-10 + 'Others' or table.
"""

from typing import Any, Dict, List, Optional, Tuple


def select_chart_kind(
    columns: List[str],
    rows: List[Dict[str, Any]],
    question_type: str = "data",
    voice_override: Optional[str] = None,
) -> str:
    """Selects the appropriate visual chart kind based on data shape and rules."""
    if voice_override:
        vo = voice_override.lower()
        if "donut" in vo or "pie" in vo:
            return "donut"
        if "stacked" in vo:
            return "stacked_bar"
        if "hbar" in vo or "horizontal bar" in vo:
            return "hbar"
        if "bar" in vo:
            return "bar"
        if "line" in vo:
            return "line"
        if "table" in vo:
            return "table"
        if "waterfall" in vo:
            return "waterfall"
        if "kpi" in vo:
            return "kpi"

    # Single row / single number KPI
    if len(rows) == 1 and len(columns) <= 2:
        return "kpi"

    # What-if scenario
    if question_type == "what_if":
        return "waterfall"

    col_names_lower = [c.lower() for c in columns]

    # Time Series (fiscal_year, year, month, date)
    time_cols = [c for c in col_names_lower if any(t in c for t in ["year", "fiscal_year", "month", "quarter", "date"])]
    if time_cols and len(rows) >= 3:
        return "line"

    # Executive tenure by grade (C1 pattern) -> Donut by grade (UX Spec §6)
    if any("grade" in c for c in col_names_lower) and len(rows) <= 12:
        return "donut"

    # Ranking (sorted top fields, vendors, assets)
    if any(k in " ".join(col_names_lower) for k in ["rank", "loss", "profit", "spend", "cost", "deficit", "implication", "vacanc"]) and len(rows) <= 15:
        return "hbar"

    # Single category measure <= 7 items -> Donut
    if 2 <= len(rows) <= 7:
        return "donut"

    # Standard bar for <= 12 categories
    if len(rows) <= 12:
        return "bar"

    return "table"


def detect_unit(columns: List[str], val_col: str) -> str:
    """Detects unit string from column names. Guarantees headcounts never receive currency."""
    v_low = val_col.lower()
    if any(k in v_low for k in ["count", "headcount", "executives", "officers", "personnel", "posts", "vacanc", "employees"]):
        return "executives"
    if any(k in v_low for k in ["cr", "inr"]):
        return "₹ Cr"
    if any(k in v_low for k in ["usd", "boe"]):
        return "$/BOE"
    if any(k in v_low for k in ["pct", "percent", "rate", "share"]):
        return "%"
    return "count"


def build_chart_spec(
    kind: str,
    columns: List[str],
    rows: List[Dict[str, Any]],
    title: Optional[str] = None,
    unit: Optional[str] = None,
    sort: Optional[str] = None,
    top_n: Optional[int] = None,
) -> Dict[str, Any]:
    """Builds a declarative chart_spec conforming to the JSON schema."""
    if not rows:
        return {
            "kind": "bar",
            "data": [],
        }

    # If kind is table, default to bar for chart_spec
    if kind == "table":
        kind = "bar"

    # Identify primary dimension and value keys
    dim_key = columns[0]
    val_key = columns[1] if len(columns) > 1 else columns[0]

    for col in columns:
        col_l = col.lower()
        if any(k in col_l for k in ["grade", "name", "id", "year", "month", "city", "asset", "term", "category", "region"]):
            dim_key = col
            break

    for col in columns:
        col_l = col.lower()
        if col != dim_key and any(k in col_l for k in ["total_executives", "executive_count", "num_executives", "count", "amount", "cost", "total", "revenue", "cr", "usd", "val", "boe", "pbt", "ebitda", "sum", "vacancies"]):
            val_key = col
            break

    # Cap categories at 12: group remainder into 'Others' if categorical bar/donut
    data = rows
    if kind in ("donut", "bar", "hbar") and len(rows) > 12:
        top_items = rows[:10]
        other_val = 0
        for r in rows[10:]:
            try:
                other_val += float(r.get(val_key, 0) or 0)
            except Exception:
                other_val += 1
        other_row = {dim_key: "Others", val_key: other_val}
        data = top_items + [other_row]

    resolved_unit = unit or detect_unit(columns, val_key)

    spec: Dict[str, Any] = {
        "kind": kind,
        "data": data,
        "x": dim_key,
        "y": val_key,
        "category": dim_key,
        "value": val_key,
        "unit": resolved_unit,
    }

    if sort in ("asc", "desc", "none"):
        spec["sort"] = sort
    if top_n:
        spec["top_n"] = top_n

    return spec
