"""Chart Selection Rules, Arbitrary Plot Kind Extractor, Histogram Binner, and Declarative ECharts Spec Generator.
Implements UX Spec §6 + Plotly/Dash visual best practices to determine optimal visualizations
and honor any explicit user request to plot as a histogram, pie, donut, bar, hbar, stacked_bar,
line, area, combo, scatter, waterfall, treemap, heatmap, bullet, gauge, funnel, map, or table.
"""

import math
import re
from typing import Any, Dict, List, Optional, Tuple


CHART_KIND_PATTERNS: List[Tuple[str, str]] = [
    (r"(?:\b(?:histogram|frequency\s+distribution|bell\s+curve|distribution\s+plot|binned\s+plot)\b|हिस्टोग्राम)", "histogram"),
    (r"(?:\b(?:donut\s+chart|donut\s+plot|doughnut\s+chart|doughnut|donut|ring\s+chart)\b|डोनट)", "donut"),
    (r"(?:\b(?:pie\s+chart|pie\s+plot|pie\s+graph|as\s+a\s+pie|in\s+a\s+pie|draw\s+a\s+pie|plot\s+a\s+pie|pie)\b|पाई\s*चार्ट|पाई)", "pie"),
    (r"(?:\b(?:horizontal\s+bar|h-bar|hbar|ranked\s+bar)\b|हॉरिजॉन्टल\s*बार)", "hbar"),
    (r"(?:\b(?:stacked\s+bar|stacked\s+column|stacked\s+chart)\b|स्टैक्ड\s*बार)", "stacked_bar"),
    (r"(?:\b(?:grouped\s+bar|grouped\s+column|side\s+by\s+side\s+bar)\b|ग्रुप्ड\s*बार)", "grouped_bar"),
    (r"(?:\b(?:scatter\s+plot|scatter\s+chart|bubble\s+chart|bubble\s+plot|scatter)\b|स्कैटर)", "scatter"),
    (r"(?:\b(?:waterfall\s+chart|waterfall\s+plot|bridge\s+chart|waterfall)\b|वॉटरफॉल|वाटरफॉल)", "waterfall"),
    (r"(?:\b(?:treemap|tree\s+map|hierarchy\s+map)\b|ट्रीमैप)", "treemap"),
    (r"(?:\b(?:heatmap|heat\s+map|matrix\s+plot)\b|हीटमैप)", "heatmap"),
    (r"(?:\b(?:area\s+chart|area\s+plot|area\s+graph|filled\s+line)\b|एरिया\s*चार्ट)", "area"),
    (r"(?:\b(?:combo\s+chart|dual\s+axis|bar\s+and\s+line)\b|कॉम्बो\s*चार्ट)", "combo"),
    (r"(?:\b(?:bullet\s+chart|target\s+bar)\b|बुलेट\s*चार्ट)", "bullet"),
    (r"(?:\b(?:gauge\s+chart|speedometer|meter\s+chart|gauge)\b|गेज\s*चार्ट)", "gauge"),
    (r"(?:\b(?:funnel\s+chart|funnel\s+plot|funnel)\b|फ़नल|फनल)", "funnel"),
    (r"(?:\b(?:line\s+chart|line\s+plot|line\s+graph|trend\s+line)\b|लाइन\s*चार्ट)", "line"),
    (r"(?:\b(?:bar\s+chart|bar\s+plot|bar\s+graph|column\s+chart|vertical\s+bar)\b|बार\s*चार्ट)", "bar"),
    (r"(?:\b(?:india\s+map|geo\s+map|on\s+a\s+map|show\s+map)\b|मैप)", "map"),
    (r"(?:\b(?:as\s+a\s+table|in\s+a\s+table|table\s+view|tabular\s+view|data\s+table)\b|टेबल|तालिका)", "table"),
]


def extract_requested_chart_kind(query: str) -> Optional[str]:
    """Extracts an explicitly requested chart/plot kind from a user query, if present."""
    if not query:
        return None
    q_low = query.lower()
    # Revenue and cost/expense/levies/profit bridge plot requests always map to a waterfall chart
    if (
        re.search(r"\b(revenue|income|sales|turnover)\b", q_low)
        and re.search(r"\b(cost\w*|expense\w*|opex|levies|outflow\w*|deduction\w*|profit|pbt|pat|margin\w*)\b", q_low)
        and re.search(r"\b(plot\w*|chart\w*|graph\w*|visual\w*|draw|show|display|bridge|waterfall)\b", q_low)
        and not re.search(r"\b(table|tabular)\b", q_low)
    ):
        return "waterfall"
    for pattern, kind in CHART_KIND_PATTERNS:
        if re.search(pattern, q_low):
            return kind
    return None


def is_pure_replot_request(query: str) -> Tuple[bool, Optional[str]]:
    """Checks if the user is asking to re-plot the currently displayed data into another chart type
    (e.g. 'plot this as a pie chart', 'draw a bar chart', 'make it a donut', 'show as a treemap').
    """
    req_kind = extract_requested_chart_kind(query)
    if not req_kind:
        return False, None

    q_low = query.lower().strip()
    # If the user mentions a new domain metric/entity that requires a fresh SQL query
    # (unless they say "this", "it", "same", "current", or it's a short command <= 8 words)
    new_topic_keywords = [
        "ahmedabad", "mumbai", "delhi", "dehradun", "assam", "ankleshwar", "mehsana", "cambay",
        "rajahmundry", "kakinada", "tripura", "cauvery", "chennai", "kolkata", "bokaro", "hazira", "uran",
        "age", "salary", "pay", "overtime", "apar", "lifting cost", "water cut", "pbt", "ebitda",
        "revenue", "capex", "csr", "mou", "vacancy", "vacancies", "brent", "training", "grievance",
    ]
    has_anaphora = any(w in q_low for w in ["this", "that", "it", "current", "same", "above", "screen"])
    has_new_topic = any(re.search(r"\b" + re.escape(k) + r"\b", q_low) for k in new_topic_keywords)

    if has_anaphora and not has_new_topic:
        return True, req_kind
    if len(q_low.split()) <= 7 and not has_new_topic and req_kind != "histogram":
        return True, req_kind
    return False, req_kind


def compute_histogram_bins(
    rows: List[Dict[str, Any]],
    val_col: str,
    num_bins: int = 8,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Bins raw numeric values into contiguous histogram intervals with frequency counts & density."""
    vals: List[float] = []
    for r in rows:
        v = r.get(val_col)
        if v is not None:
            try:
                fv = float(v)
                if math.isfinite(fv):
                    vals.append(fv)
            except Exception:
                pass

    if not vals:
        return rows, list(rows[0].keys()) if rows else ["bucket", "count"]

    vmin, vmax = min(vals), max(vals)
    if vmin == vmax:
        return [{"bucket": f"{vmin:g}", "count": len(vals), "share_pct": 100.0}], ["bucket", "count", "share_pct"]

    n = len(vals)
    bins = max(4, min(12, num_bins or int(math.ceil(math.log2(n) + 1))))
    step = (vmax - vmin) / bins
    # Round step nicely if range is large
    if step >= 5:
        step = round(step)
        vmin = math.floor(vmin)

    buckets: List[Dict[str, Any]] = []
    counts = [0] * bins
    for v in vals:
        idx = int((v - vmin) / step) if step > 0 else 0
        if idx >= bins:
            idx = bins - 1
        if idx < 0:
            idx = 0
        counts[idx] += 1

    for i in range(bins):
        low = vmin + i * step
        high = vmin + (i + 1) * step
        if step >= 2:
            label = f"{low:,.0f}–{high:,.0f}"
        else:
            label = f"{low:.1f}–{high:.1f}"
        buckets.append({
            "bucket": label,
            "bin_mid": round((low + high) / 2.0, 2),
            "count": counts[i],
            "share_pct": round(counts[i] * 100.0 / max(1, n), 1),
        })

    return buckets, ["bucket", "count", "share_pct"]


def select_chart_kind(
    columns: List[str],
    rows: List[Dict[str, Any]],
    question_type: str = "data",
    voice_override: Optional[str] = None,
    query: Optional[str] = None,
) -> str:
    """Selects the appropriate visual chart kind based on explicit user request, voice override, or data shape."""
    # 1. Explicit voice override or user query chart request ALWAYS wins
    for candidate in (voice_override, query):
        if candidate:
            req = extract_requested_chart_kind(candidate)
            if req:
                return req
            vo = candidate.lower().strip()
            if vo in {
                "pie", "donut", "bar", "column", "hbar", "stacked_bar", "grouped_bar", "line", "area",
                "combo", "histogram", "treemap", "heatmap", "waterfall", "bullet", "gauge",
                "funnel", "scatter", "kpi", "table", "map",
            }:
                return vo

    # 1b. Nothing to plot (e.g. a failed or empty query): a table, never an IndexError
    if not columns or not rows:
        return "table"

    # 2. Single row / single number KPI
    if len(rows) == 1 and len(columns) <= 2:
        return "kpi"

    # 3. What-if scenario
    if question_type == "what_if":
        return "waterfall"

    col_names_lower = [c.lower() for c in columns]

    # 4. Histogram / Bucketed distribution columns
    if any(k in col_names_lower[0] for k in ["bucket", "bin", "band", "range", "bracket"]):
        return "histogram"

    # 5. Time Series (fiscal_year, year, month, date)
    time_cols = [c for c in col_names_lower if any(t in c for t in ["year", "fiscal_year", "month", "quarter", "date"])]
    if time_cols and len(rows) >= 3:
        return "line"

    # 6. Ordered grade / level breakdown (SPEC-07 §4.1–4.2, BUG-34) -> Column chart in level order
    grade_cols = [c for c in columns if "grade" in c.lower()]
    if grade_cols and len(columns) == 2:
        distinct_grades = {str(r.get(grade_cols[0])) for r in rows}
        if len(distinct_grades) <= 16:
            return "column"

    # 7. Ranking (sorted top fields, vendors, assets)
    if any(k in " ".join(col_names_lower) for k in ["rank", "loss", "profit", "pbt", "ebitda", "revenue", "spend", "cost", "deficit", "implication", "vacanc"]) and len(rows) <= 60:
        return "hbar"

    # 8. Single category measure <= 7 items -> Donut
    if 2 <= len(rows) <= 7:
        return "donut"

    # 9. Standard bar for <= 15 categories, hbar for <= 30
    if len(rows) <= 15:
        return "bar"
    if len(rows) <= 30:
        return "hbar"

    return "table"


def detect_unit(columns: List[str], val_col: str) -> str:
    """Detects unit string from column names. Guarantees headcounts never receive currency."""
    v_low = val_col.lower()
    if any(k in v_low for k in ["count", "headcount", "executives", "officers", "personnel", "posts", "vacanc", "employees", "apprentice"]):
        return "employees"
    if any(k in v_low for k in ["cr", "crore"]):
        return "₹ Cr"
    if "lakh" in v_low:
        return "₹ Lakh"
    if any(k in v_low for k in ["inr", "pay", "salary", "allowance", "hra", "dearness", "prp", "bonus", "overtime", "ctc", "rupee", "amount"]):
        return "₹"
    if any(k in v_low for k in ["usd", "per_boe", "cost_boe"]):
        return "$/BOE"
    if "boe" in v_low:
        return "BOE"
    if any(k in v_low for k in ["pct", "percent", "rate", "share"]):
        return "%"
    if any(k in v_low for k in ["hour", "hrs"]):
        return "hours"
    if re.search(r"(?:^|_)(?:years?|yrs?|age|tenure|stay)(?:$|_)", v_low):
        return "years"
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
    """Builds a declarative chart_spec conforming to answer_contract.schema.json."""
    if not rows or not columns:
        return {
            "kind": "bar",
            "data": [],
        }

    if kind == "table":
        kind = "bar"

    # Identify primary dimension and value keys
    dim_key = columns[0]
    val_key = columns[1] if len(columns) > 1 else columns[0]
    secondary_val_key: Optional[str] = None

    for col in columns:
        col_l = col.lower()
        if any(k in col_l for k in ["bucket", "bin", "band", "range", "grade", "name", "discipline", "work_centre", "wc_name", "field_name", "asset", "sector", "state", "id", "year", "month", "city", "term", "category", "region"]):
            dim_key = col
            break

    numeric_cols: List[str] = []
    for col in columns:
        if col == dim_key:
            continue
        # Check if column has numeric values in rows
        for r in rows[:10]:
            v = r.get(col)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                numeric_cols.append(col)
                break
            elif isinstance(v, str):
                try:
                    float(v.replace(",", ""))
                    numeric_cols.append(col)
                    break
                except Exception:
                    pass

    if numeric_cols:
        val_key = numeric_cols[0]
        for col in numeric_cols:
            col_l = col.lower()
            if any(k in col_l for k in ["total_executives", "executive_count", "num_executives", "executives", "officers", "headcount", "employees", "count", "amount", "cost", "total", "revenue", "cr", "usd", "boe", "pbt", "ebitda", "sum", "vacancies", "score", "hours"]):
                val_key = col
                break
        remaining_num = [c for c in numeric_cols if c != val_key]
        if remaining_num:
            secondary_val_key = remaining_num[0]

    # If single-row entity with multiple numeric columns (e.g. Ankleshwar Asset Revenue, EBITDA, PBT):
    # build a 5-step P&L waterfall bridge when waterfall is requested, or pivot numeric columns into rows!
    all_num_cols = [col for col in columns if isinstance(rows[0].get(col), (int, float)) and not isinstance(rows[0].get(col), bool)]
    if len(rows) == 1 and len(all_num_cols) >= 2:
        r0 = rows[0]
        rev_c = next((c for c in all_num_cols if "revenue" in c.lower()), None)
        ebitda_c = next((c for c in all_num_cols if "ebitda" in c.lower()), None)
        pbt_c = next((c for c in all_num_cols if "pbt" in c.lower() or "profit" in c.lower()), None)
        if kind == "waterfall" and rev_c and pbt_c:
            rev_v = float(r0.get(rev_c) or 0)
            pbt_v = float(r0.get(pbt_c) or 0)
            ebitda_v = float(r0.get(ebitda_c) or round((rev_v + pbt_v) / 2.0, 2)) if ebitda_c else round(rev_v * 0.68, 2)
            opex_v = round(ebitda_v - rev_v, 2)
            dda_v = round(pbt_v - ebitda_v, 2)
            wf_rows = [
                {"step": "Gross Revenue", "amount_cr": rev_v, "type": "base"},
                {"step": "OPEX & Levies", "amount_cr": opex_v, "type": "loss"},
                {"step": "EBITDA", "amount_cr": ebitda_v, "type": "total"},
                {"step": "DD&A", "amount_cr": dda_v, "type": "loss"},
                {"step": "PBT (Net)", "amount_cr": pbt_v, "type": "total"},
            ]
            return {
                "kind": "waterfall",
                "data": wf_rows,
                "x": "step",
                "y": "amount_cr",
                "category": "step",
                "value": "amount_cr",
                "unit": unit or "₹ Cr",
            }
        piv_rows = [
            {"metric": col.replace("_cr", " (₹ Cr)").replace("_", " ").title(), "value": float(r0.get(col) or 0)}
            for col in all_num_cols
        ]
        return {
            "kind": kind,
            "data": piv_rows,
            "x": "metric",
            "y": "value",
            "category": "metric",
            "value": "value",
            "unit": unit or detect_unit(columns, val_key),
        }

    # If kind == 'histogram' and rows are NOT already bucketed, auto-bin them!
    is_already_bucketed = any(k in dim_key.lower() for k in ["bucket", "bin", "band", "range", "bracket", "group", "grade"]) or (
        len(rows) <= 16 and any(k in val_key.lower() for k in ["count", "employees", "executives", "frequency", "officers", "fields"])
    )
    if kind == "histogram" and not is_already_bucketed and len(rows) > 12:
        binned_rows, binned_cols = compute_histogram_bins(rows, val_key)
        dim_key = binned_cols[0]
        val_key = binned_cols[1]
        data = binned_rows
    else:
        # Aggregate duplicate dimension keys for single-series categorical charts
        agg_map: Dict[str, Dict[str, Any]] = {}
        has_duplicate_dims = len({str(r.get(dim_key)) for r in rows}) < len(rows)
        if has_duplicate_dims and kind in ("pie", "donut", "bar", "hbar", "treemap", "funnel"):
            for r in rows:
                dk = str(r.get(dim_key, "Unknown"))
                if dk not in agg_map:
                    agg_map[dk] = {dim_key: r.get(dim_key)}
                    for col in columns:
                        if col != dim_key:
                            v = r.get(col)
                            if isinstance(v, (int, float)) and not isinstance(v, bool):
                                agg_map[dk][col] = 0
                for col in columns:
                    if col != dim_key and col in agg_map[dk]:
                        v = r.get(col)
                        if isinstance(v, (int, float)) and not isinstance(v, bool):
                            agg_map[dk][col] += v
            data = list(agg_map.values())
        else:
            data = list(rows)

    # Cap slices for pie/donut at 12 with 'Others'
    if kind in ("pie", "donut") and len(data) > 12:
        top_items = data[:10]
        other_val = 0.0
        for r in data[10:]:
            try:
                other_val += float(r.get(val_key, 0) or 0)
            except Exception:
                other_val += 1.0
        other_row = {dim_key: "Others", val_key: round(other_val, 2)}
        data = top_items + [other_row]
    elif kind in ("bar", "hbar") and len(data) > 25:
        data = data[:25]

    resolved_unit = unit or detect_unit(columns, val_key)

    spec: Dict[str, Any] = {
        "kind": kind,
        "data": data,
        "x": secondary_val_key if (kind == "scatter" and secondary_val_key) else dim_key,
        "y": val_key,
        "category": dim_key,
        "value": val_key,
        "unit": resolved_unit,
    }
    if secondary_val_key:
        spec["series"] = secondary_val_key

    if sort in ("asc", "desc", "none"):
        spec["sort"] = sort
    if top_n:
        spec["top_n"] = top_n

    return spec
