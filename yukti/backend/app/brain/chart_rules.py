"""Deterministic chart selection, explicit chart-kind precedence, and ChartSpec builder.

Implements SPEC-09 §4.4 (explicit chart-kind precedence, EN + HI, tested against the shared
30-utterance fixture `yukti/contracts/fixtures/kind_precedence_30.json`) and SPEC-09 §4.3 /
BUG-08 / BUG-09 / BUG-22 (no fabricated subtotals or expenses synthesis; PBT column
matcher never matches PAT or generic "profit").
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple

CHART_KINDS = (
    "table",
    "bar",
    "hbar",
    "stacked_bar",
    "stacked_100",
    "grouped_bar",
    "pie",
    "donut",
    "histogram",
    "box",
    "line",
    "area",
    "combo",
    "scatter",
    "bubble",
    "waterfall",
    "treemap",
    "sunburst",
    "heatmap",
    "sankey",
    "funnel",
    "tornado",
    "bullet",
    "gauge",
    "kpi",
    "map",
)

# P4.1 (BUG-09): strict PBT matcher — matches only explicit PBT / profit-before-tax, never PAT or generic "profit".
PBT_COLUMN_RE = re.compile(r"(?:^|[\s_])pbt(?:$|[\s_])|profit[_\s]+before[_\s]+tax", re.IGNORECASE)
PAT_COLUMN_RE = re.compile(r"(?:^|[\s_])pat(?:$|[\s_])|profit[_\s]+after[_\s]+tax|net[_\s]+profit", re.IGNORECASE)


def is_pbt_column(col_name: str) -> bool:
    """Return True only when `col_name` refers to Profit Before Tax (never PAT or generic profit)."""
    if not col_name or PAT_COLUMN_RE.search(col_name):
        return False
    return bool(PBT_COLUMN_RE.search(col_name))


# Longest / most specific phrases first so "horizontal bar" never matches "bar" and "stacked bar" never matches "bar".
# Exact Python twin of `LEXICON` in `yukti/frontend/src/charts/kindPrecedence.ts`.
_PRECEDENCE_LEXICON: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b100\s*%\s*stacked\b", re.I), "stacked_100"),
    (re.compile(r"\bstacked\s+(bar|column)s?\b|\bstacked\b", re.I), "stacked_bar"),
    (re.compile(r"\b(grouped|clustered)\s+(bar|column)s?\b", re.I), "grouped_bar"),
    (re.compile(r"\bhorizontal\s+bars?\b|\bh-?bar\b|\branked\s+bars?\b|क्षैतिज\s*बार", re.I), "hbar"),
    (re.compile(r"\bcombo\b|\bdual[-\s]axis\b", re.I), "combo"),
    (re.compile(r"\bbox\s*(plot|chart)?\b|\bbox-?and-?whisker\b|बॉक्स\s*प्लॉट", re.I), "box"),
    (re.compile(r"\bbullet\s+(chart|graph)\b|\bbullet\b", re.I), "bullet"),
    (re.compile(r"\bgauge\b|\bdial\s+chart\b|\bspeedometer\b", re.I), "gauge"),
    (re.compile(r"\bheat\s*map\b|\bmatrix\s+chart\b|हीटमैप", re.I), "heatmap"),
    (re.compile(r"\bhistogram\b|\bbell\s+curve\b|\bfrequency\s+distribution\b|हिस्टोग्राम", re.I), "histogram"),
    (re.compile(r"\bscatter(\s*plot|\s*chart)?\b|स्कैटर", re.I), "scatter"),
    (re.compile(r"\bbubble\b", re.I), "bubble"),
    (re.compile(r"\btree\s*map\b|ट्रीमैप", re.I), "treemap"),
    (re.compile(r"\bsunburst\b", re.I), "sunburst"),
    (re.compile(r"\bsankey\b", re.I), "sankey"),
    (re.compile(r"\btornado\b", re.I), "tornado"),
    (re.compile(r"\bfunnel\b", re.I), "funnel"),
    (re.compile(r"\bdonut\b|\bdoughnut\b|\bring\s+chart\b|डोनट", re.I), "donut"),
    (re.compile(r"\bpie\b|पाई", re.I), "pie"),
    (re.compile(r"\barea\s+(chart|graph|plot)\b|एरिया\s*चार्ट", re.I), "area"),
    (re.compile(r"\bwaterfall\b|वॉटरफॉल|वाटरफॉल", re.I), "waterfall"),
    (re.compile(r"\bline\s+(chart|graph|plot)\b|\bas\s+a\s+line\b|रेखा\s*चार्ट|रेखा|लाइन\s*चार्ट", re.I), "line"),
    (re.compile(r"\b(bar|column)\s*(chart|graph|plot|view)?s?\b|कॉलम\s*चार्ट|कॉलम|बार\s*चार्ट", re.I), "bar"),
    (re.compile(r"\btabular(\s+form)?\b|\b(in|as)\s+a\s+table\b|\btable\b|सारणी|टेबल|तालिका", re.I), "table"),
    (re.compile(r"\b(india|state)\s+map\b|\bon\s+an?\s+(india\s+)?map\b|\bmap\b", re.I), "map"),
]

_BRIDGE_RE = re.compile(
    r"\bbridge\b|\bwalk\s+(me\s+)?from\b|\bfrom\s+revenue\s+to\s+(net\s+)?(profit|pat|pbt)\b|ब्रिज",
    re.I,
)
_TREND_RE = re.compile(
    r"\btrend\b|\bover\s+(the\s+)?(last\s+|past\s+)?\d+\s+years?\b|ट्रेंड",
    re.I,
)


def resolve_kind(utterance: str) -> Optional[str]:
    """Resolve chart kind from utterance using SPEC-09 §4.4 precedence order.

    1. Explicit chart kind keyword in the utterance (EN + HI) always wins.
    2. Explicit bridge wording ("bridge", "walk me from ...", "from revenue to profit/PAT") -> "waterfall".
    3. Multi-year trend wording ("trend", "over the last N years") -> "line".
    4. Otherwise returns None so the data-shape default applies.
    """
    s = (utterance or "").strip()
    if not s:
        return None
    for pat, kind in _PRECEDENCE_LEXICON:
        if pat.search(s):
            return kind
    if _BRIDGE_RE.search(s):
        return "waterfall"
    if _TREND_RE.search(s):
        return "line"
    return None


def extract_requested_chart_kind(query: str) -> Optional[str]:
    """Detect if the user explicitly requested a specific chart type in their query or voice command."""
    return resolve_kind(query)


def is_pure_replot_request(query: str) -> Tuple[bool, Optional[str]]:
    """Return `(True, chart_kind)` ONLY when the query is a pure re-plot of current screen data,
    NOT a new analytical question (e.g. 'draw a histogram of employee ages in Ahmedabad' -> False).
    """
    raw = (query or "").strip()
    q = raw.lower().rstrip("?!.।")
    if not q:
        return False, None

    # Short direct commands (EN + HI)
    direct_map = {
        "table": "table",
        "show as table": "table",
        "show as a table": "table",
        "show in tabular form": "table",
        "in tabular form": "table",
        "view as table": "table",
        "table view": "table",
        "switch to table": "table",
        "टेबल": "table",
        "सारणी": "table",
        "टेबल में दिखाओ": "table",
        "सारणी में दिखाओ": "table",
        "इसे टेबल में दिखाओ": "table",
        "इसे सारणी में दिखाओ": "table",
        "pie chart": "pie",
        "show as pie": "pie",
        "show as pie chart": "pie",
        "show as a pie chart": "pie",
        "plot as pie chart": "pie",
        "plot this as a pie chart": "pie",
        "switch to pie chart": "pie",
        "पाई चार्ट": "pie",
        "इसे पाई चार्ट में दिखाओ": "pie",
        "एसेट डेटा को पाई चार्ट में दिखाओ": "pie",
        "donut": "donut",
        "donut chart": "donut",
        "doughnut chart": "donut",
        "show as donut": "donut",
        "show as a donut chart": "donut",
        "plot as donut chart": "donut",
        "डोनट चार्ट": "donut",
        "इसे डोनट चार्ट में दिखाओ": "donut",
        "एसेट डेटा को डोनट चार्ट में बदलो": "donut",
        "bar": "bar",
        "bar chart": "bar",
        "column chart": "bar",
        "show as bar": "bar",
        "show as bar chart": "bar",
        "show as a bar chart": "bar",
        "plot as bar chart": "bar",
        "switch to bar chart": "bar",
        "बार चार्ट": "bar",
        "कॉलम चार्ट": "bar",
        "इसे कॉलम चार्ट में दिखाओ": "bar",
        "इसे बार चार्ट में दिखाओ": "bar",
        "horizontal bar": "hbar",
        "horizontal bar chart": "hbar",
        "show as horizontal bar": "hbar",
        "show as a horizontal bar chart": "hbar",
        "hbar": "hbar",
        "histogram": "histogram",
        "show as histogram": "histogram",
        "show as a histogram": "histogram",
        "plot this as a histogram": "histogram",
        "line chart": "line",
        "show as line": "line",
        "show as a line chart": "line",
        "plot as line chart": "line",
        "रेखा चार्ट": "line",
        "इसे रेखा चार्ट में दिखाओ": "line",
        "area chart": "area",
        "show as area chart": "area",
        "scatter": "scatter",
        "scatter plot": "scatter",
        "show as scatter plot": "scatter",
        "treemap": "treemap",
        "show as treemap": "treemap",
        "heatmap": "heatmap",
        "show as heatmap": "heatmap",
        "waterfall": "waterfall",
        "waterfall chart": "waterfall",
        "show as waterfall": "waterfall",
        "show as a waterfall": "waterfall",
        "show as a waterfall chart": "waterfall",
        "show this as a waterfall": "waterfall",
        "show this as a waterfall chart": "waterfall",
        "plot this as a waterfall": "waterfall",
        "plot this as a waterfall chart": "waterfall",
        "express this as a waterfall": "waterfall",
        "express it as a waterfall": "waterfall",
        "can you express it as a waterfall": "waterfall",
        "can you express this as a waterfall": "waterfall",
        "वॉटरफॉल": "waterfall",
        "वॉटरफॉल चार्ट": "waterfall",
        "इसे वॉटरफॉल में दिखाओ": "waterfall",
        "इसे वॉटरफॉल चार्ट में दिखाओ": "waterfall",
        "वाटरफॉल चार्ट में दिखाओ": "waterfall",
    }
    if q in direct_map:
        return True, direct_map[q]

    # Hindi follow-up complaints when a waterfall re-plot did not change the screen (fedback2 / BEH-07.34)
    if re.search(r"(वॉटरफॉल|वाटरफॉल).*(दिख\s+नहीं\s+रहा|नहीं\s+दिख\s+रहा)", q) or q in (
        "नहीं बदला गया",
        "नहीं, यह वॉटरफॉल चार्ट्स दिख नहीं रहा है",
        "नहीं यह वॉटरफॉल चार्ट्स दिख नहीं रहा है",
        "नहीं, यह वॉटरफॉल चार्ट दिख नहीं रहा है",
    ):
        return True, "waterfall"

    # Generic pronoun-based re-plot in EN or HI ("can you express it as a waterfall", "convert this to a line chart",
    # "इसे वॉटरफॉल में दिखाओ", "एसेट डेटा को डोनट चार्ट में बदलो")
    is_en_pronoun_replot = bool(
        re.match(
            r"^(?:can\s+you\s+|could\s+you\s+|please\s+)*(?:show|view|plot|draw|switch|make|express|display|convert|change|turn|present|redraw)\s+(?:this|it|that|current\s+(?:data|view|chart|table))\b",
            q,
        )
    )
    is_hi_pronoun_replot = bool(
        re.match(
            r"^(?:कृपया\s+)?(?:इसे|इसको|यह|इस\s+डेटा\s+को|एसेट\s+डेटा\s+को)\s+.*(?:दिखाओ|दिखाइए|बनाओ|बना\s+दो|बदलो|बदल\s+दो)$",
            q,
        )
    )
    if is_en_pronoun_replot or is_hi_pronoun_replot:
        k = resolve_kind(q)
        if k:
            return True, k

    # Match "plot/show/switch/view (this/it/current data) as a <chart>" only if there are no domain filters or FYs
    domain_words = [
        "ahmedabad", "mumbai", "delhi", "dehradun", "assam", "mehsana", "ankleshwar", "cambay",
        "jorhat", "tripura", "rajahmundry", "cauvery", "kakinada", "vadodara", "kolkata", "chennai",
        "hazira", "uran", "bokaro", "agartala", "silchar", "nazira", "karaikal", "panvel", "goa",
        "age", "ages", "salary", "pay", "tenure", "stay", "lifting", "water cut", "production",
        "vacancy", "vacancies", "overtime", "apar", "grade", "discipline", "employee", "employees",
        "executive", "executives", "field", "fields", "brent", "mou", "capex", "revenue", "pbt", "pat", "ebitda",
        "p&l", "pnl", "profit and loss", "income statement", "balance sheet", "cash flow",
    ]
    if any(w in q for w in domain_words) or re.search(r"\bfy\s*\d{2}\b|\b20\d{2}\s*[-–]\s*\d{2}\b", q):
        return False, None

    kind = resolve_kind(q)
    if kind and len(q.split()) <= 8 and any(
        v in q for v in ["plot", "show", "switch", "view", "make", "change", "display", "convert", "draw", "express", "दिखाओ", "बदलो", "बनाओ"]
    ):
        return True, kind

    return False, None


def compute_histogram_bins(
    rows: List[Dict[str, Any]],
    value_col: str,
    num_bins: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Bin raw numeric rows into frequency intervals for a true statistical histogram + bell curve."""
    vals: List[float] = []
    for r in rows:
        v = r.get(value_col)
        if v is not None:
            try:
                fv = float(v)
                if math.isfinite(fv):
                    vals.append(fv)
            except (TypeError, ValueError):
                pass

    if not vals:
        return [], ["bucket", "count", "share_pct", "normal_fit"]

    n = len(vals)
    min_v = min(vals)
    max_v = max(vals)
    if min_v == max_v:
        return [
            {
                "bucket": f"{round(min_v, 1)}",
                "count": n,
                "share_pct": 100.0,
                "normal_fit": n,
            }
        ], ["bucket", "count", "share_pct", "normal_fit"]

    k = num_bins or max(5, min(10, int(round(1 + 3.322 * math.log10(max(2, n))))))
    raw_step = (max_v - min_v) / k
    if raw_step >= 50:
        step = float(round(raw_step / 25.0) * 25 or 25)
    elif raw_step >= 10:
        step = float(round(raw_step / 5.0) * 5 or 5)
    elif raw_step >= 2:
        step = float(round(raw_step))
    else:
        step = round(raw_step, 1) or 0.5

    start = math.floor(min_v / step) * step
    bins: List[Dict[str, Any]] = []
    mean = sum(vals) / n
    variance = sum((x - mean) ** 2 for x in vals) / max(1, n - 1)
    std = math.sqrt(variance) if variance > 0 else step

    curr = start
    while curr < max_v + 1e-9 and len(bins) < 14:
        nxt = curr + step
        is_last = nxt >= max_v - 1e-9
        cnt = sum(1 for x in vals if (curr <= x <= nxt if is_last else curr <= x < nxt))
        mid = (curr + nxt) / 2.0
        z = (mid - mean) / std if std > 0 else 0.0
        pdf = (1.0 / (std * math.sqrt(2 * math.pi))) * math.exp(-0.5 * z * z) if std > 0 else 0.0
        normal_expected = round(n * step * pdf, 1)

        if step >= 1 and float(curr).is_integer() and float(nxt).is_integer():
            label = f"{int(curr)}–{int(nxt)}"
        else:
            label = f"{curr:.1f}–{nxt:.1f}"

        bins.append(
            {
                "bucket": label,
                "count": cnt,
                "share_pct": round((cnt * 100.0) / n, 1),
                "normal_fit": normal_expected,
            }
        )
        curr = nxt

    return bins, ["bucket", "count", "share_pct", "normal_fit"]


def select_chart_kind(
    columns: List[str],
    rows: List[Dict[str, Any]],
    question_type: str = "data",
    voice_override: Optional[str] = None,
    utterance: Optional[str] = None,
) -> str:
    """Select the appropriate chart kind following SPEC-09 §4.4 precedence:

    1. Explicit chart kind in `voice_override` or `utterance` (always wins).
    2. Question type (`policy`, `document`, `refusal`).
    3. Data-shape default.
    """
    if voice_override and voice_override in CHART_KINDS:
        return voice_override

    if utterance:
        explicit = resolve_kind(utterance)
        if explicit and explicit in CHART_KINDS:
            return explicit

    if question_type in ("policy", "document", "refusal"):
        return "table"

    if not rows or not columns:
        return "table"

    num_rows = len(rows)
    num_cols = len(columns)

    if num_rows == 1 and num_cols <= 3:
        return "kpi"

    col_lower = [c.lower() for c in columns]

    if any(k in col_lower for k in ["bucket", "bin", "age_band", "tenure_band", "salary_band", "bracket"]):
        return "histogram"

    if any(k in col_lower for k in ["month", "year", "fiscal_year", "quarter", "date", "period", "fy"]):
        if num_rows >= 2:
            return "line"

    if any(k in " ".join(col_lower) for k in ["delta", "variance", "impact", "bridge", "shock", "change_cr"]):
        return "waterfall"

    if any(k in " ".join(col_lower) for k in ["target", "excellent", "achievement", "mou", "score"]):
        return "hbar"

    if 2 <= num_rows <= 6 and num_cols == 2:
        val_col = columns[1]
        vals = [r.get(val_col) for r in rows if isinstance(r.get(val_col), (int, float))]
        if vals and all(v >= 0 for v in vals):
            return "donut"

    if 2 <= num_rows <= 15 and num_cols >= 2:
        dim_col = columns[0].lower()
        if any(k in dim_col for k in ["grade", "grade_id", "level", "year", "fy", "quarter"]):
            return "bar"
        return "hbar"

    return "table"


def detect_unit(columns: List[str], val_key: str) -> str:
    """Detect the human-readable unit from column names."""
    vk = (val_key or "").lower()
    joined = " ".join(c.lower() for c in columns)
    if "cr" in vk or "crore" in vk or "inr_cr" in joined:
        return "₹ Cr"
    if "lakh" in vk:
        return "₹ Lakh"
    if "usd" in vk or "per_boe" in vk or "lifting_cost" in vk:
        return "$/BOE"
    if "pct" in vk or "percent" in vk or "share" in vk or "margin" in vk or "rate" in vk:
        return "%"
    if "boe" in vk:
        return "BOE"
    if "year" in vk or "yr" in vk or "tenure" in vk or "age" in vk:
        return "yrs"
    if "month" in vk:
        return "months"
    if "hour" in vk or "ot_" in vk:
        return "hrs"
    if any(k in vk for k in ["employee", "executive", "officer", "headcount", "count", "vacanc", "post"]):
        return "employees"
    return ""


def build_chart_spec(
    kind: str,
    columns: List[str],
    rows: List[Dict[str, Any]],
    title: Optional[str] = None,
    unit: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a complete ECharts-ready ChartSpec dictionary for the frontend canvas.

    P4.1 (BUG-08, BUG-09):
    - When `kind == "waterfall"` and `rows` carry statement `line_code`s, delegate to
      `app.brain.bridge.bridge()` so the waterfall is a signed accounting bridge.
    - Never fabricate subtotals or synthetic deductions from a single row.
    """
    if not rows or not columns:
        return {"kind": "table", "data": [], "title": title}

    if kind not in CHART_KINDS:
        kind = "bar"

    # If waterfall is requested on statement rows carrying `line_code`, build a verified bridge.
    if kind == "waterfall":
        has_typed = all(isinstance(r.get("type"), str) and r.get("type") in ("total", "delta") for r in rows)
        if has_typed:
            dim_k = "step" if "step" in rows[0] else (columns[0] if columns else "label")
            val_k = "amount_cr" if "amount_cr" in rows[0] else (columns[1] if len(columns) > 1 else "value")
            return {
                "kind": "waterfall",
                "title": title,
                "data": rows[:40],
                "x": dim_k,
                "y": val_k,
                "category": dim_k,
                "value": val_k,
                "unit": unit or "₹ Cr",
                "sort": "none",
            }
        has_line_code = any(isinstance(r.get("line_code"), str) for r in rows)
        if has_line_code:
            from app.brain.bridge import BridgeOk, bridge

            b_res = bridge(rows)
            if isinstance(b_res, BridgeOk):
                return b_res.to_chart_spec(title=title)

    # Identify primary dimension and value keys
    dim_key = columns[0]
    val_key = columns[1] if len(columns) > 1 else columns[0]
    secondary_val_key: Optional[str] = None

    for col in columns:
        col_l = col.lower()
        if any(
            k in col_l
            for k in [
                "bucket", "bin", "band", "range", "grade", "name", "discipline",
                "work_centre", "wc_name", "field_name", "asset", "sector", "state",
                "id", "year", "month", "city", "term", "category", "region",
            ]
        ):
            dim_key = col
            break

    numeric_cols: List[str] = []
    for col in columns:
        if col == dim_key:
            continue
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
            if any(
                k in col_l
                for k in [
                    "total_executives", "executive_count", "num_executives", "executives",
                    "officers", "headcount", "employees", "count", "amount", "cost",
                    "total", "revenue", "cr", "usd", "boe", "pbt", "pat", "ebitda",
                    "sum", "vacancies", "score", "hours",
                ]
            ):
                val_key = col
                break
        remaining_num = [c for c in numeric_cols if c != val_key]
        if remaining_num:
            secondary_val_key = remaining_num[0]

    # Single-row entity with multiple numeric measures: pivot measures into plain metric rows.
    # P4.1 (BUG-09): never synthesise subtotals or expense plugs from a single row.
    all_num_cols = [
        col for col in columns
        if isinstance(rows[0].get(col), (int, float)) and not isinstance(rows[0].get(col), bool)
    ]
    if len(rows) == 1 and len(all_num_cols) >= 2:
        r0 = rows[0]
        piv_rows = [
            {"metric": col.replace("_cr", " (₹ Cr)").replace("_", " ").title(), "value": float(r0.get(col) or 0)}
            for col in all_num_cols
        ]
        eff_kind = "bar" if kind == "waterfall" else kind
        return {
            "kind": eff_kind,
            "title": title,
            "data": piv_rows,
            "x": "metric",
            "y": "value",
            "category": "metric",
            "value": "value",
            "unit": unit or detect_unit(columns, val_key),
        }

    is_already_bucketed = any(
        k in dim_key.lower() for k in ["bucket", "bin", "band", "range", "bracket", "group", "grade"]
    ) or (
        len(rows) <= 16
        and any(k in val_key.lower() for k in ["count", "employees", "executives", "frequency", "officers", "fields"])
    )
    if kind == "histogram" and not is_already_bucketed and len(rows) > 12:
        binned_rows, binned_cols = compute_histogram_bins(rows, val_key)
        dim_key = binned_cols[0]
        val_key = binned_cols[1]
        data = binned_rows
    else:
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
                            agg_map[dk][col] = float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v
                else:
                    for col in numeric_cols:
                        v = r.get(col)
                        if isinstance(v, (int, float)) and not isinstance(v, bool):
                            agg_map[dk][col] = round(float(agg_map[dk].get(col, 0) or 0) + float(v), 2)
            data = list(agg_map.values())
            if kind in ("hbar", "pie", "donut", "treemap", "funnel"):
                data.sort(
                    key=lambda x: float(x.get(val_key, 0) or 0)
                    if isinstance(x.get(val_key), (int, float))
                    else 0.0,
                    reverse=True,
                )
        else:
            data = rows[:40]

    detected_unit = unit if unit is not None else detect_unit(columns, val_key)

    spec: Dict[str, Any] = {
        "kind": kind,
        "data": data,
        "x": dim_key if kind != "hbar" else val_key,
        "y": val_key if kind != "hbar" else dim_key,
        "category": dim_key,
        "value": val_key,
    }
    if secondary_val_key:
        spec["series"] = secondary_val_key
    if title:
        spec["title"] = title
    if detected_unit:
        spec["unit"] = detected_unit
    if kind in ("hbar", "bar") and len(data) > 10:
        spec["top_n"] = 12
        spec["sort"] = "desc"

    return spec
