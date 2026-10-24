"""Presenter (B2): result -> visual, deterministic narration, context chips.

Numbers in the narration come only from the query result (BUILD.md principle 1). B4 adds
the insight library, drill-down chips and the numeric-grounding check on top of this.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.brain.compiler import GRADE_LEVEL_ORDER, CompiledQuery, QueryResult
from app.brain.query_spec import QuerySpec
from app.semantic.entities import get_entities
from app.tools.chart_rules import build_chart_spec, select_chart_kind
from app.brain.statement_builder import build_statement_spec, v3_field_enabled
from app.brain.semantic_model import get_semantic_model

EXEC_LEVELS: List[str] = ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9"]
ALL_NON_BOARD_LEVELS: List[str] = ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "GRP-B", "GRP-C", "GRP-D"]
LEVEL_CHART_NOTE = "Levels are categories, so this is a column chart in level order."


def _station_short_name(wc_id: Optional[str]) -> str:
    if not wc_id:
        return "ONGC"
    if wc_id == "WC-DEL":
        return "Delhi"
    ents = get_entities()
    wc_meta = ents.work_centres.get(wc_id) or {}
    city = str(wc_meta.get("city") or "").strip()
    return city or ents.wc_name(wc_id)


def _format_exemption(r: Dict[str, Any]) -> str:
    ex = r.get("exemption")
    if ex is not None:
        s = str(ex).strip()
        if s and s.upper() not in ("NONE", "NULL", "FALSE", "—", "-"):
            if s.upper() == "SUPERANNUATION":
                return "Pre-retirement (≤2 yrs)"
            return s.replace("_", "-").title()
    if r.get("is_superannuation_exempt") in (True, 1, "true", "True"):
        return "Pre-retirement (≤2 yrs)"
    return "—"


def format_workforce_roster_table(
    spec: QuerySpec,
    compiled: CompiledQuery,
    columns: List[str],
    rows: List[Dict[str, Any]],
    n_total: Optional[int],
    persona: str = "CMD",
    query: str = "",
) -> Tuple[Dict[str, Any], bool]:
    """Formats a workforce roster table per SPEC-07 §4.3 and board #77 contract.

    Returns `(table_dict, used_grade_designation_fallback)`.
    """
    cap = 2000
    q_low = (query or "").lower()
    if spec.self_scope or re.search(r"\b(salary|pay|ctc|gross|apar|rating|score|vigilance|posh|medical|leave)\b", q_low):
        return {
            "columns": columns,
            "rows": rows[:cap],
            "total_rows": n_total if n_total is not None else len(rows),
        }, False

    is_delhi = (compiled.station_wc_id in (None, "WC-DEL")) and not any(
        f.field == "wc" and f.value not in ("WC-DEL", ["WC-DEL"]) for f in (spec.filters or [])
    )
    station_short = _station_short_name(compiled.station_wc_id)
    tenure_key = "delhi_tenure_years" if is_delhi else "station_tenure_years"
    tenure_label = "Tenure in Delhi (yrs)" if is_delhi else f"Tenure at {station_short} (yrs)"

    visible_cols = [
        "name",
        "functional_designation",
        "grade",
        "ongc_tenure_years",
        tenure_key,
        "years_to_retirement",
        "exemption",
    ]
    can_keep_hidden = (persona or "").strip().upper() in ("CMD", "DIR_HR", "DIR_FIN")
    hidden_cols = ["emp_id", "discipline"] if can_keep_hidden else []
    all_cols = visible_cols + hidden_cols

    out_rows: List[Dict[str, Any]] = []
    used_fallback = False
    for r in rows[:cap]:
        if not r.get("current_designation"):
            used_fallback = True
        desig = r.get("functional_designation") or r.get("current_designation") or r.get("designation") or r.get("grade") or ""
        t_val = r.get("delhi_tenure_years") if r.get("delhi_tenure_years") is not None else r.get("station_tenure_years")
        ongc_val = r.get("ongc_tenure_years")
        ret_val = r.get("years_to_retirement")
        row_out: Dict[str, Any] = {
            "name": r.get("name"),
            "functional_designation": desig,
            "grade": r.get("grade"),
            "ongc_tenure_years": round(float(ongc_val), 1) if isinstance(ongc_val, (int, float)) else ongc_val,
            tenure_key: round(float(t_val), 1) if isinstance(t_val, (int, float)) else t_val,
            "years_to_retirement": round(float(ret_val), 1) if isinstance(ret_val, (int, float)) else ret_val,
            "exemption": _format_exemption(r),
        }
        if can_keep_hidden:
            row_out["emp_id"] = r.get("emp_id")
            row_out["discipline"] = r.get("discipline")
        out_rows.append(row_out)

    column_labels = {
        "name": "Name",
        "functional_designation": "Designation",
        "grade": "Level",
        "ongc_tenure_years": "ONGC service (yrs)",
        tenure_key: tenure_label,
        "years_to_retirement": "Years to retirement",
        "exemption": "Exemption",
    }
    tbl: Dict[str, Any] = {
        "columns": all_cols,
        "rows": out_rows,
        "total_rows": n_total if n_total is not None else len(rows),
        "column_labels": column_labels,
        "hidden_columns": hidden_cols,
        "default_sort": {"key": tenure_key, "dir": "desc"},
        "as_of": get_semantic_model().anchor_date,
    }
    return tbl, used_fallback


def order_workforce_grade_rows(
    spec: QuerySpec,
    compiled: CompiledQuery,
    val_col: str,
    rows: List[Dict[str, Any]],
    raw_rows: Optional[List[Dict[str, Any]]] = None
) -> Tuple[List[Dict[str, Any]], int, int, int]:
    """Separates CMD/DIR board rows and orders level rows explicitly by `GRADE_LEVEL_ORDER`.

    Returns `(ordered_rows, cmd_count, dir_count, total_including_board)`.
    """
    cmd_n = 0
    dir_n = 0
    total_with_board = 0
    source_for_totals = raw_rows if raw_rows is not None else rows
    for r in source_for_totals:
        g = str(r.get("grade") or "").strip().upper()
        v = _num(r.get(val_col))
        total_with_board += int(round(v))
        if g == "CMD":
            cmd_n += int(round(v))
        elif g == "DIR":
            dir_n += int(round(v))
            
    by_grade: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        g = str(r.get("grade") or "").strip().upper()
        if g not in ("CMD", "DIR") and g:
            by_grade[g] = dict(r)

    has_explicit_grade_filter = any(f.field == "grade" for f in (spec.filters or []))
    is_exec_only = (
        (compiled.definition_id in ("DELHI_GT5_CONT_V1", "STATION_GT5_CONT_V1") and not compiled.all_cadres)
        or any(f.field == "cadre" and str(f.value).lower() == "executive" for f in (spec.filters or []))
    )
    if has_explicit_grade_filter:
        target_levels = sorted(by_grade.keys(), key=lambda g: GRADE_LEVEL_ORDER.get(g, 99))
    elif is_exec_only:
        target_levels = list(EXEC_LEVELS)
    else:
        target_levels = list(ALL_NON_BOARD_LEVELS)

    ordered: List[Dict[str, Any]] = []
    for lvl in target_levels:
        if lvl in by_grade:
            ordered.append(by_grade[lvl])
        else:
            ordered.append({"grade": lvl, val_col: 0})
    return ordered, cmd_n, dir_n, total_with_board

UNIT_WORDS = {"employees": "employees", "posts": "posts", "workers": "contract workers", "inr_cr": "₹ crore",
              "inr_lakh": "₹ lakh", "usd_per_boe": "$/BOE", "inr_per_boe": "₹/BOE", "pct": "%", "years": "years", "hours": "hours",
              "boe": "BOE", "mmtoe": "MMTOE", "incidents": "incidents", "ratio": "", "score": "", "parameters": "parameters"}
CHART_UNIT = {"employees": "employees", "posts": "employees", "workers": "employees", "inr_cr": "₹ Cr",
              "inr_lakh": "₹ Lakh", "usd_per_boe": "$/BOE", "inr_per_boe": "₹/BOE", "pct": "%", "years": "years",
              "hours": "hours", "boe": "BOE", "mmtoe": "MMTOE"}
DIM_PLURAL = {"discipline": "disciplines", "work_centre": "work centres", "grade": "grades", "field": "fields",
              "asset": "assets", "fiscal_year": "years", "fy": "years", "cadre": "cadres", "gender": "groups"}


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
        out.append(f"As of {get_semantic_model().anchor_date}")
    return out


def _resolve_stmt_periods(ep: Dict[str, Any], periods: Optional[List[str]]) -> Optional[List[str]]:
    """Derives explicit latest-first period list from `periods` or `effective_period.from..to` (S6)."""
    if periods:
        return list(periods)
    if ep.get("from") and ep.get("to"):
        m_lo = re.search(r"(\d{2})$", str(ep["from"]))
        m_hi = re.search(r"(\d{2})$", str(ep["to"]))
        if m_lo and m_hi:
            lo_y, hi_y = int(m_lo.group(1)), int(m_hi.group(1))
            if hi_y >= lo_y:
                return [f"FY{y:02d}" for y in range(hi_y, lo_y - 1, -1)]
    return None


def build_visual(spec: QuerySpec, compiled: CompiledQuery, columns: List[str], rows: List[Dict[str, Any]],
                 chart_kind: Optional[str], title: str, subtitle: str, mode: str,
                 n_total: Optional[int] = None,
                 breakdown: Optional[Tuple[List[str], List[Dict[str, Any]]]] = None,
                 persona: str = "CMD",
                 query: str = "",
                 raw_rows: Optional[List[Dict[str, Any]]] = None,
                 periods: Optional[List[str]] = None) -> Dict[str, Any]:
    unit = CHART_UNIT.get(compiled.unit)
    unit_word = UNIT_WORDS.get(compiled.unit, "")
    cap = 2000 if compiled.grain == "row" else 200   # rosters ship whole (UI virtualises, U5.2)
    table: Dict[str, Any] = {"columns": columns, "rows": rows[:cap], "total_rows": n_total if n_total is not None else len(rows)}
    vis: Dict[str, Any] = {"type": "table", "mode": mode, "title": title, "subtitle": subtitle, "table": table}
    if not rows:
        return vis
    if compiled.grain == "row":
        if compiled.subject == "workforce":
            roster_tbl, used_fallback = format_workforce_roster_table(
                spec, compiled, columns, rows, n_total, persona=persona, query=query
            )
            vis["table"] = roster_tbl
            if used_fallback:
                vis["_designation_fallback"] = True
            return vis
        # MoU target scorecard is row-grain (10 parameters) but always renders a horizontal target chart + summary KPIs
        if compiled.subject == "mou" and "parameter" in columns and "pct_of_excellent" in columns:
            ck = chart_kind if chart_kind and chart_kind != "table" else "hbar"
            chart = build_chart_spec(kind=ck, columns=["parameter", "pct_of_excellent"], rows=rows, title=title, unit="%")
            chart["target"] = 100
            vis["type"] = "chart"
            vis["chart"] = chart
            num_rows = [r for r in rows if isinstance(r.get("pct_of_excellent"), (int, float))]
            if num_rows:
                top_r = max(num_rows, key=lambda r: _num(r.get("pct_of_excellent")))
                low_r = min(num_rows, key=lambda r: _num(r.get("pct_of_excellent")))
                on_track = sum(1 for r in num_rows if _num(r.get("pct_of_excellent")) >= 95.0)
                vis["kpis"] = [
                    {"label": "MoU Parameters", "value": len(rows), "unit": "parameters", "delta": f"{on_track} of {len(rows)} ≥95% target"},
                    {"label": "Highest vs Target", "value": round(_num(top_r.get("pct_of_excellent")), 1), "unit": "%", "delta": str(top_r.get("parameter") or "")},
                    {"label": "Weakest vs Target", "value": round(_num(low_r.get("pct_of_excellent")), 1), "unit": "%", "delta": str(low_r.get("parameter") or "")},
                ]
        return vis
    dims = [alias for _, alias in compiled.dims]
    val = compiled.value_columns[0] if compiled.value_columns else (columns[-1] if columns else None)

    def _pick_code(by_code_map: Dict[str, Dict[str, Any]], *codes: str) -> Dict[str, Any]:
        for c in codes:
            if c in by_code_map and by_code_map[c]:
                return by_code_map[c]
        return {}

    if compiled.metric == "pnl_statement" and (
        (dims and dims[0] == "line_item")
        or any(isinstance(r, dict) and ("line_code" in r or "values" in r or "fiscal_year" in r) for r in rows)
    ):
        # Single-FY or Multi-FY Schedule III Statement of Profit & Loss
        from app.brain.bridge import BridgeOk, bridge, bridge_chart_rows
        from app.brain.statement_builder import build_statement_spec, v3_field_enabled

        ep = compiled.effective_period or {}
        fy = ep.get("fy", "FY26")
        stmt_periods = _resolve_stmt_periods(ep, periods)
        if not stmt_periods:
            fys_found = sorted(list({str(r["fiscal_year"]) for r in rows if "fiscal_year" in r}), reverse=True)
            if len(fys_found) > 1:
                stmt_periods = fys_found

        scope_str = "standalone"
        for f in spec.filters:
            if f.field == "scope":
                scope_str = f.value[0] if isinstance(f.value, list) else f.value

        stmt_spec = build_statement_spec(
            statement="pnl",
            rows=rows,
            periods=stmt_periods,
            fy=fy,
            scope=scope_str,
            title=title or "Statement of Profit and Loss (Standalone)",
            include_prior_from_single_fy=(stmt_periods is None),
        )
        emit_stmt = v3_field_enabled("statement")
        default_table_type = "statement" if emit_stmt else "table"
        if emit_stmt:
            vis["statement"] = stmt_spec
        if stmt_spec.get("periods"):
            fy = stmt_spec["periods"][0]

        by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
        rev_r = _pick_code(by_code, "PL.REV_OPS", "gross_revenue_inr_cr", "REV_OPS")
        eb_r = by_code.get("ebitda_inr_cr") or {}
        pat_r = _pick_code(by_code, "PL.PAT", "pat_inr_cr", "PAT")
        cpat_r = by_code.get("consolidated_pat_inr_cr") or {}
        rev_val = rev_r.get("amount_cr") if "amount_cr" in rev_r else (rev_r.get("values") or {}).get(fy)
        eb_val = eb_r.get("amount_cr") if "amount_cr" in eb_r else (eb_r.get("values") or {}).get(fy)
        pat_val = pat_r.get("amount_cr") if "amount_cr" in pat_r else (pat_r.get("values") or {}).get(fy)
        cpat_val = cpat_r.get("amount_cr") if "amount_cr" in cpat_r else (cpat_r.get("values") or {}).get(fy)
        kpis = [
            {
                "label": f"Revenue from Ops ({fy})",
                "value": rev_val,
                "unit": "₹ crore",
                "delta": f"{rev_r.get('yoy_change_pct'):+.1f}% vs prior FY" if isinstance(rev_r.get("yoy_change_pct"), (int, float)) else "",
            },
            {
                "label": f"Standalone PAT ({fy})",
                "value": pat_val,
                "unit": "₹ crore",
                "delta": f"{pat_r.get('yoy_change_pct'):+.1f}% YoY · {pat_r.get('pct_of_revenue'):.1f}% margin" if isinstance(pat_r.get("yoy_change_pct"), (int, float)) and isinstance(pat_r.get("pct_of_revenue"), (int, float)) else "",
            },
        ]
        if eb_val is not None:
            kpis.insert(
                1,
                {
                    "label": f"Standalone EBITDA ({fy})",
                    "value": eb_val,
                    "unit": "₹ crore",
                    "delta": f"{eb_r.get('pct_of_revenue'):.1f}% EBITDA margin" if isinstance(eb_r.get("pct_of_revenue"), (int, float)) else "",
                },
            )
        # M1 (SPEC-03 §5.1 rule 2): preserve Consolidated PAT KPI when flag is off; `kpis[:3]` caps when flag is on
        if cpat_val is not None:
            kpis.append(
                {
                    "label": "Consolidated PAT (Group)",
                    "value": cpat_val,
                    "unit": "₹ crore",
                    "delta": f"{cpat_r.get('yoy_change_pct'):+.1f}% YoY (Group)" if isinstance(cpat_r.get("yoy_change_pct"), (int, float)) else "Group Net Income",
                }
            )
        vis["kpis"] = kpis[:3] if emit_stmt else kpis
        # 7 clean display columns + hidden line_code so frontend re-plot can classify statement lines
        disp_cols = ["line_item", "note_ref", "amount_cr", "prior_fy_cr", "yoy_delta_cr", "yoy_change_pct", "pct_of_revenue", "line_code"]
        disp_rows = [{**r, **{k: r.get(k) for k in disp_cols}} for r in rows]
        vis["table"] = {"columns": disp_cols, "rows": disp_rows, "total_rows": len(disp_rows)}

        # P4.1 (SPEC-09 §4.3): build the signed P&L waterfall bridge from statement lines (no EBITDA plug)
        b_res = bridge(stmt_spec if emit_stmt else rows, period=fy)
        if isinstance(b_res, BridgeOk):
            ck = chart_kind if chart_kind and chart_kind not in ("kpi", "table") else "waterfall"
            if ck == "waterfall":
                vis["chart"] = b_res.to_chart_spec()
            else:
                wf_rows = bridge_chart_rows(b_res)
                vis["chart"] = build_chart_spec(
                    kind=ck,
                    columns=["step", "amount_cr"],
                    rows=wf_rows,
                    title=b_res.default_title(),
                    unit="₹ Cr",
                )
            # Table-First rule: default to structured statement visual unless a chart (e.g., waterfall) was explicitly requested
            vis["type"] = "chart" if (chart_kind and chart_kind not in ("kpi", "table")) else default_table_type
        else:
            # M3 (SPEC-09 §4.3 step 6): on BridgeError, keep statement/table, leave vis["chart"] unset, attach BridgeError copy
            vis.pop("chart", None)
            vis["type"] = default_table_type
            if chart_kind and chart_kind not in ("kpi", "table"):
                vis["note"] = b_res.message("en")
                vis["note_hi"] = b_res.message("hi")
                vis["bridge_error"] = {"code": b_res.code, "reason": b_res.reason}
        return vis

    if compiled.metric == "balance_sheet" and (
        (dims and dims[0] == "line_item")
        or any(isinstance(r, dict) and ("line_code" in r or "values" in r or "fiscal_year" in r) for r in rows)
    ):
        from app.brain.statement_builder import build_statement_spec, v3_field_enabled

        ep = compiled.effective_period or {}
        fy = ep.get("fy", "FY26")
        stmt_periods = _resolve_stmt_periods(ep, periods)
        if not stmt_periods:
            fys_found = sorted(list({str(r["fiscal_year"]) for r in rows if "fiscal_year" in r}), reverse=True)
            if len(fys_found) > 1:
                stmt_periods = fys_found

        scope_str = "standalone"
        for f in spec.filters:
            if f.field == "scope":
                scope_str = f.value[0] if isinstance(f.value, list) else f.value

        stmt_spec = build_statement_spec(
            statement="balance_sheet",
            rows=rows,
            periods=stmt_periods,
            fy=fy,
            scope=scope_str,
            title=title or "Balance Sheet (Standalone)",
            include_prior_from_single_fy=(stmt_periods is None),
        )
        emit_stmt = v3_field_enabled("statement")
        default_table_type = "statement" if emit_stmt else "table"
        if emit_stmt:
            vis["statement"] = stmt_spec
        if stmt_spec.get("periods"):
            fy = stmt_spec["periods"][0]

        by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
        ta_r = _pick_code(by_code, "BS.TOTAL_ASSETS", "total_assets_inr_cr")
        nw_r = _pick_code(by_code, "BS.EQUITY.TOTAL", "net_worth_inr_cr")
        ltd_r = _pick_code(by_code, "BS.BORROW_NC", "BS.BORROW_TOTAL_10YR", "long_term_debt_inr_cr", "BS.LIAB.LT_BORROWINGS")
        cash_r = _pick_code(by_code, "BS.CCE", "cash_and_bank_inr_cr")
        kpis = [
            {
                "label": f"Total Assets ({fy})",
                "value": ta_r.get("amount_cr") if "amount_cr" in ta_r else (ta_r.get("values") or {}).get(fy),
                "unit": "₹ crore",
                "delta": f"{ta_r.get('yoy_change_pct'):+.1f}% vs prior FY" if isinstance(ta_r.get("yoy_change_pct"), (int, float)) else "Assets = Equity + Liab",
            },
            {
                "label": f"Standalone Net Worth ({fy})",
                "value": nw_r.get("amount_cr") if "amount_cr" in nw_r else (nw_r.get("values") or {}).get(fy),
                "unit": "₹ crore",
                "delta": f"{nw_r.get('pct_of_assets'):.1f}% of Total Assets" if isinstance(nw_r.get("pct_of_assets"), (int, float)) else "",
            },
            {
                "label": f"Long-Term Borrowings ({fy})",
                "value": ltd_r.get("amount_cr") if "amount_cr" in ltd_r else (ltd_r.get("values") or {}).get(fy),
                "unit": "₹ crore",
                "delta": f"{ltd_r.get('yoy_change_pct'):+.1f}% YoY" if isinstance(ltd_r.get("yoy_change_pct"), (int, float)) else "Non-Current Borrowings",
            },
            {
                "label": f"Cash & Bank Balances ({fy})",
                "value": cash_r.get("amount_cr") if "amount_cr" in cash_r else (cash_r.get("values") or {}).get(fy),
                "unit": "₹ crore",
                "delta": f"{cash_r.get('yoy_change_pct'):+.1f}% YoY" if isinstance(cash_r.get("yoy_change_pct"), (int, float)) else "Schedule III B(ii)",
            },
        ]
        vis["kpis"] = kpis[:3] if emit_stmt else kpis
        disp_cols = ["line_item", "note_ref", "section", "amount_cr", "prior_fy_cr", "yoy_change_pct", "pct_of_assets", "line_code"]
        disp_rows = [{**r, **{k: r.get(k) for k in disp_cols}} for r in rows]
        vis["table"] = {"columns": disp_cols, "rows": disp_rows, "total_rows": len(disp_rows)}
        bs_chart_specs = [
            (("BS.ASSETS.NON_CURRENT.TOTAL", "non_current_assets_inr_cr", "BS.NCA.TOTAL"), "Non-Current Assets"),
            (("BS.ASSETS.CURRENT.TOTAL", "current_assets_inr_cr", "BS.CA.TOTAL"), "Current Assets"),
            (("BS.TOTAL_ASSETS", "total_assets_inr_cr"), "Total Assets"),
            (("BS.EQUITY.TOTAL", "net_worth_inr_cr"), "Total Equity"),
            (("BS.LIAB.NON_CURRENT.TOTAL", "non_current_liabilities_inr_cr"), "Non-Current Liabilities"),
            (("BS.LIAB.CURRENT.TOTAL", "current_liabilities_inr_cr"), "Current Liabilities"),
        ]
        bs_chart_rows = []
        for codes_tuple, lbl in bs_chart_specs:
            matched = _pick_code(by_code, *codes_tuple)
            if matched:
                bs_chart_rows.append({"bs_head": lbl, "amount_cr": matched.get("amount_cr"), "prior_fy_cr": matched.get("prior_fy_cr")})
        ck = chart_kind if chart_kind and chart_kind not in ("kpi", "table") else "bar"
        vis["chart"] = build_chart_spec(kind=ck, columns=["bs_head", "amount_cr", "prior_fy_cr"], rows=bs_chart_rows, title=title, unit="₹ Cr")
        vis["type"] = "chart" if (chart_kind and chart_kind not in ("kpi", "table")) else default_table_type
        return vis

    if compiled.metric == "cash_flow_statement" and (
        (dims and dims[0] == "line_item")
        or any(isinstance(r, dict) and ("line_code" in r or "values" in r or "fiscal_year" in r) for r in rows)
    ):
        from app.brain.statement_builder import (
            build_statement_spec,
            load_snapshot_bs_cash_by_period,
            v3_field_enabled,
        )

        ep = compiled.effective_period or {}
        fy = ep.get("fy", "FY26")
        stmt_periods = _resolve_stmt_periods(ep, periods)
        if not stmt_periods:
            fys_found = sorted(list({str(r["fiscal_year"]) for r in rows if "fiscal_year" in r}), reverse=True)
            if len(fys_found) > 1:
                stmt_periods = fys_found

        scope_str = "standalone"
        for f in spec.filters:
            if f.field == "scope":
                scope_str = f.value[0] if isinstance(f.value, list) else f.value

        stmt_spec = build_statement_spec(
            statement="cash_flow",
            rows=rows,
            periods=stmt_periods,
            fy=fy,
            scope=scope_str,
            title=title or "Statement of Cash Flows (Standalone)",
            include_prior_from_single_fy=(stmt_periods is None),
            bs_cash_by_period=load_snapshot_bs_cash_by_period(),
        )
        emit_stmt = v3_field_enabled("statement")
        default_table_type = "statement" if emit_stmt else "table"
        if emit_stmt:
            vis["statement"] = stmt_spec
        if stmt_spec.get("periods"):
            fy = stmt_spec["periods"][0]

        by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
        ocf_r = _pick_code(by_code, "CF.CFO", "operating_cash_flow_inr_cr")
        icf_r = _pick_code(by_code, "CF.CFI", "investing_cash_flow_inr_cr")
        fcf_r = _pick_code(by_code, "CF.FCF", "free_cash_flow_inr_cr", "CF.CFF", "financing_cash_flow_inr_cr")
        cls_r = _pick_code(by_code, "CF.CCE_CLOSE", "closing_cash_inr_cr")
        kpis = [
            {
                "label": f"Operating Cash Flow ({fy})",
                "value": ocf_r.get("amount_cr") if "amount_cr" in ocf_r else (ocf_r.get("values") or {}).get(fy),
                "unit": "₹ crore",
                "delta": f"{ocf_r.get('yoy_change_pct'):+.1f}% vs prior FY" if isinstance(ocf_r.get("yoy_change_pct"), (int, float)) else "Ind-AS 7 OCF",
            },
            {
                "label": f"Investing Cash Flow ({fy})",
                "value": icf_r.get("amount_cr") if "amount_cr" in icf_r else (icf_r.get("values") or {}).get(fy),
                "unit": "₹ crore",
                "delta": "Capex + JVs net of Dividends",
            },
            {
                "label": f"Free Cash Flow ({fy})",
                "value": fcf_r.get("amount_cr") if "amount_cr" in fcf_r else (fcf_r.get("values") or {}).get(fy),
                "unit": "₹ crore",
                "delta": f"{fcf_r.get('pct_of_ocf'):.1f}% of OCF" if isinstance(fcf_r.get("pct_of_ocf"), (int, float)) else "Ind-AS 7 CFF",
            },
            {
                "label": f"Closing Cash & Bank ({fy})",
                "value": cls_r.get("amount_cr") if "amount_cr" in cls_r else (cls_r.get("values") or {}).get(fy),
                "unit": "₹ crore",
                "delta": f"{cls_r.get('yoy_change_pct'):+.1f}% vs prior FY" if isinstance(cls_r.get("yoy_change_pct"), (int, float)) else "Ind-AS 7 Closing CCE",
            },
        ]
        vis["kpis"] = kpis[:3] if emit_stmt else kpis
        disp_cols = ["line_item", "note_ref", "section", "amount_cr", "prior_fy_cr", "yoy_delta_cr", "pct_of_ocf", "line_code"]
        disp_rows = [{**r, **{k: r.get(k) for k in disp_cols}} for r in rows]
        vis["table"] = {"columns": disp_cols, "rows": disp_rows, "total_rows": len(disp_rows)}
        pbt_v = _num(_pick_code(by_code, "CF.START_PROFIT", "pbt_inr_cr").get("amount_cr"))
        nc_wc_v = round(
            _num(_pick_code(by_code, "CF.ADJ_SUBTOTAL", "non_cash_adjustments_cf_inr_cr").get("amount_cr"))
            + _num(_pick_code(by_code, "CF.WC_SUBTOTAL", "working_capital_change_cf_inr_cr").get("amount_cr")),
            2,
        )
        tax_p_v = -abs(_num(_pick_code(by_code, "CF.TAX_PAID", "income_tax_paid_cf_inr_cr").get("amount_cr")))
        ocf_v = _num(ocf_r.get("amount_cr"))
        icf_v = _num(icf_r.get("amount_cr"))
        fcf_act_v = _num(_pick_code(by_code, "CF.CFF", "financing_cash_flow_inr_cr").get("amount_cr"))
        net_chg_v = _num(_pick_code(by_code, "CF.NET_CHANGE_CCE", "net_cash_change_inr_cr").get("amount_cr"))
        cf_wf_rows = [
            {"cf_stage": "Profit Before Tax", "amount_cr": pbt_v, "type": "total"},
            {"cf_stage": "Non-Cash & WC Adj", "amount_cr": nc_wc_v, "type": "delta"},
            {"cf_stage": "Cash Taxes Paid", "amount_cr": tax_p_v, "type": "delta"},
            {"cf_stage": "Operating Cash Flow", "amount_cr": ocf_v, "type": "total"},
            {"cf_stage": "Investing Cash Flow", "amount_cr": icf_v, "type": "delta"},
            {"cf_stage": "Financing Cash Flow", "amount_cr": fcf_act_v, "type": "delta"},
            {"cf_stage": "Net Cash Change", "amount_cr": net_chg_v, "type": "total"},
        ]
        ck = chart_kind if chart_kind and chart_kind not in ("kpi", "table") else "waterfall"
        vis["chart"] = build_chart_spec(kind=ck, columns=["cf_stage", "amount_cr"], rows=cf_wf_rows, title=title, unit="₹ Cr")
        vis["type"] = "chart" if (chart_kind and chart_kind not in ("kpi", "table")) else default_table_type
        return vis

    if compiled.metric == "financial_ratios" and dims and dims[0] == "line_item":
        fy = (compiled.effective_period or {}).get("fy", "FY26")
        by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
        ebm_r = _pick_code(by_code, "RATIO.PBIDT_MARGIN_PCT", "ebitda_margin_pct")
        roce_r = _pick_code(by_code, "RATIO.ROCE", "standalone_roce_pct")
        roe_r = _pick_code(by_code, "RATIO.ROE_INCL_EXC", "roe_pct")
        de_r = _pick_code(by_code, "RATIO.DEBT_EQUITY", "debt_to_equity_ratio")
        vis["kpis"] = [
            {"label": f"PBIDT Margin ({fy})", "value": ebm_r.get("value"), "unit": "%", "delta": "Operating Profitability"},
            {"label": f"Standalone ROCE ({fy})", "value": roce_r.get("value"), "unit": "%", "delta": "Return on Capital Employed"},
            {"label": f"Return on Equity ({fy})", "value": roe_r.get("value"), "unit": "%", "delta": "PAT / Net Worth"},
            {"label": f"Debt-to-Equity ({fy})", "value": de_r.get("value"), "unit": "x", "delta": "Total Debt / Net Worth"},
        ]
        disp_cols = ["line_item", "category", "unit", "value", "prior_fy_value", "yoy_delta", "formula", "line_code"]
        disp_rows = [{**r, **{k: r.get(k) for k in disp_cols}} for r in rows]
        vis["table"] = {"columns": disp_cols, "rows": disp_rows, "total_rows": len(disp_rows)}
        pct_rows = [r for r in rows if r.get("unit") == "%"]
        ck = chart_kind if chart_kind and chart_kind not in ("kpi", "table") else "bar"
        vis["chart"] = build_chart_spec(kind=ck, columns=["line_item", "value", "prior_fy_value"], rows=pct_rows, title=title, unit="%")
        vis["type"] = "chart" if (chart_kind and chart_kind not in ("kpi", "table")) else "table"
        return vis
    if not dims or (len(rows) == 1 and breakdown and breakdown[1] and len(breakdown[1]) >= 2 and chart_kind != "waterfall"):
        r0 = rows[0]
        vis["kpis"] = [{"label": compiled.metric_label if c == compiled.metric else c.replace("_", " ").title(),
                        "value": r0.get(c), "unit": unit_word if c == compiled.metric else "₹ crore" if c.endswith("_cr") else ""}
                       for c in compiled.value_columns[:3] if c in r0]
        if chart_kind == "waterfall" and len(compiled.value_columns) >= 2:
            vis["type"] = "chart"
            vis["chart"] = build_chart_spec(kind="waterfall", columns=columns, rows=rows, title=title, unit=unit)
            return vis
        if breakdown and breakdown[1] and len(breakdown[0]) >= 2:
            bd_cols, bd_rows = breakdown
            bd_dim, bd_val = bd_cols[0], bd_cols[1]
            if compiled.subject == "workforce" and bd_dim == "grade" and compiled.metric == "headcount":
                ordered_bd, cmd_n, dir_n, _ = order_workforce_grade_rows(spec, compiled, bd_val, bd_rows, raw_rows=None)
                bd_rows = ordered_bd
                ck = chart_kind if (chart_kind and chart_kind not in ("kpi", "table", "histogram", "bar")) else "column"
                vis["type"] = "chart"
                chart_bd = build_chart_spec(kind=ck, columns=[bd_dim, bd_val], rows=bd_rows, title=title, unit=unit)
                chart_bd["x_order"] = "explicit"
                chart_bd["note"] = LEVEL_CHART_NOTE
                if cmd_n > 0 or dir_n > 0:
                    st_short = _station_short_name(compiled.station_wc_id)
                    chart_bd["footnote"] = f"Also in {st_short}: CMD {cmd_n}, Directors {dir_n}"
                vis["chart"] = chart_bd
                vis["table"] = {"columns": [bd_dim, bd_val], "rows": bd_rows, "total_rows": len(bd_rows)}
            else:
                ck = chart_kind if chart_kind and chart_kind not in ("kpi", "table") else (
                    "line" if bd_dim in ("fiscal_year", "fy") else select_chart_kind(columns=[bd_dim, bd_val], rows=bd_rows)
                )
                if ck in ("kpi", "table"):
                    ck = "hbar"
                vis["type"] = "kpi"
                vis["chart"] = build_chart_spec(kind=ck, columns=[bd_dim, bd_val] + [c for c in bd_cols[2:5]], rows=bd_rows, title=title, unit=unit)
            num_bd = [r for r in bd_rows if isinstance(r.get(bd_val), (int, float)) and not isinstance(r.get(bd_val), bool)]
            if num_bd:
                top_b = max(num_bd, key=lambda r: _num(r.get(bd_val)))
                low_b = min(num_bd, key=lambda r: _num(r.get(bd_val)))
                if bd_dim in ("fiscal_year", "fy"):
                    vis["kpis"].append({"label": f"10-Yr Peak · {top_b.get(bd_dim)}", "value": top_b.get(bd_val), "unit": unit_word, "delta": "FY17–FY26 High"})
                    if len(num_bd) > 1:
                        vis["kpis"].append({"label": f"10-Yr Trough · {low_b.get(bd_dim)}", "value": low_b.get(bd_val), "unit": unit_word, "delta": "FY17–FY26 Low"})
                else:
                    vis["kpis"].append({"label": f"Largest {bd_dim.replace('_', ' ').title()}", "value": top_b.get(bd_val), "unit": unit_word, "delta": str(top_b.get(bd_dim) or "")})
                    if len(num_bd) > 1:
                        vis["kpis"].append({"label": f"Smallest {bd_dim.replace('_', ' ').title()}", "value": low_b.get(bd_val), "unit": unit_word, "delta": str(low_b.get(bd_dim) or "")})
            return vis
        if not dims:
            vis["type"] = "kpi"
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
    if compiled.subject == "workforce" and dims == ["grade"] and compiled.metric == "headcount" and val:
        ordered_rows, cmd_n, dir_n, total_with_board = order_workforce_grade_rows(spec, compiled, val, rows, raw_rows=raw_rows)
        st_short = _station_short_name(compiled.station_wc_id)
        exec_num_rows = [
            r for r in ordered_rows
            if str(r.get("grade")) in EXEC_LEVELS and isinstance(r.get(val), (int, float)) and not isinstance(r.get(val), bool)
        ]
        if not compiled.definition_id and exec_num_rows:
            top_ex = max(exec_num_rows, key=lambda r: _num(r.get(val)))
            top_ex_lvl = str(top_ex.get("grade"))
            top_ex_n = int(round(_num(top_ex.get(val))))
            title = f"{st_short}: {total_with_board:,} staff; {top_ex_lvl} is the largest executive level ({top_ex_n:,})"
            vis["title"] = title
        vis["table"] = {"columns": columns, "rows": ordered_rows, "total_rows": len(ordered_rows)}
        ck_lvl = chart_kind if (chart_kind and chart_kind not in ("kpi", "histogram", "bar")) else "column"
        if ck_lvl != "table":
            vis["type"] = "chart"
            chart_lvl = build_chart_spec(
                kind=ck_lvl,
                columns=["grade", val] + [c for c in compiled.value_columns[1:] if c != val],
                rows=ordered_rows,
                title=title,
                unit=unit,
            )
            chart_lvl["x_order"] = "explicit"
            chart_lvl["note"] = LEVEL_CHART_NOTE
            if cmd_n > 0 or dir_n > 0:
                chart_lvl["footnote"] = f"Also in {st_short}: CMD {cmd_n}, Directors {dir_n}"
            if any('<5' in str(r.get(val, '')) for r in rows):
                chart_lvl["footnote"] = chart_lvl.get("footnote", "") + (" · " if chart_lvl.get("footnote") else "") + "cells <5 suppressed"
            vis["chart"] = chart_lvl
        kpis_lvl: List[Dict[str, Any]] = [
            {
                "label": f"Total {st_short} Staff" if st_short != "ONGC" else "Total Active Staff",
                "value": total_with_board,
                "unit": unit_word,
                "delta": (f"Also in {st_short}: CMD {cmd_n}, Directors {dir_n}" if (cmd_n or dir_n) else f"Across {len(ordered_rows)} levels") + (" (cells <5 suppressed)" if any('<5' in str(r.get(val, '')) for r in rows) else ""),
            }
        ]
        if exec_num_rows:
            top_ex = max(exec_num_rows, key=lambda r: _num(r.get(val)))
            kpis_lvl.append(
                {
                    "label": f"Largest Executive Level · {top_ex.get('grade')}",
                    "value": top_ex.get(val),
                    "unit": unit_word,
                }
            )
        vis["kpis"] = kpis_lvl[:3]
        return vis
    kind = chart_kind or ("line" if dims[0] == "fiscal_year" else select_chart_kind(columns=[dims[0], val], rows=rows))
    if kind == "kpi":
        kind = "bar"
    if kind != "table":
        vis["type"] = "chart"
        vis["chart"] = build_chart_spec(kind=kind, columns=[dims[0], val] + [c for c in compiled.value_columns[1:] if c != val],
                                        rows=rows, title=title, unit=unit)
        # Consistent summary KPI strip on every dimensional chart
        num_rows = [r for r in rows if isinstance(r.get(val), (int, float)) and not isinstance(r.get(val), bool)]
        if num_rows and not vis.get("kpis"):
            top_r = max(num_rows, key=lambda r: _num(r.get(val)))
            low_r = min(num_rows, key=lambda r: _num(r.get(val)))
            kpis: List[Dict[str, Any]] = []
            if is_additive(compiled):
                tot = round(sum(_num(r.get(val)) for r in num_rows), 2)
                if abs(tot - round(tot)) < 1e-9:
                    tot = int(round(tot))
                plural = DIM_PLURAL.get(dims[0], "groups")
                kpis.append({"label": f"Total {compiled.metric_label}", "value": tot, "unit": unit_word, "delta": f"Across {len(num_rows)} {plural}"})
            kpis.append({"label": f"Highest · {top_r.get(dims[0])}", "value": top_r.get(val), "unit": unit_word})
            if len(num_rows) > 1:
                kpis.append({"label": f"Lowest · {low_r.get(dims[0])}", "value": low_r.get(val), "unit": unit_word})
            vis["kpis"] = kpis[:3]
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
        sorted_by_stay = (not spec.sort) or (spec.sort.by in ("station_tenure_years", "delhi_tenure_years") and spec.sort.dir == "desc")
        stay_val = first.get("delhi_tenure_years") if first.get("delhi_tenure_years") is not None else first.get("station_tenure_years")
        desig_val = first.get("functional_designation") or first.get("designation") or first.get("grade")
        if compiled.subject == "workforce" and first.get("name") and sorted_by_stay and stay_val is not None:
            lead += (f" The longest station stay is {first.get('name')}, {desig_val}, "
                     f"at {fmt_num(stay_val)} years.")
        elif compiled.subject == "mou":
            weakest = min(rows, key=lambda r: float(r.get("pct_of_excellent") or 0))
            lead = (f"{len(rows)} MoU parameters ({scope}). Weakest against the Excellent target: "
                    f"{weakest.get('parameter')} at {fmt_num(weakest.get('pct_of_excellent'), 'pct')} of target.")
        return lead + " The full list is on screen."
    dims = [alias for _, alias in compiled.dims]
    val = compiled.value_columns[0] if compiled.value_columns else None

    def _pick_n(by_code_map: Dict[str, Dict[str, Any]], *codes: str) -> Dict[str, Any]:
        for c in codes:
            if c in by_code_map and by_code_map[c]:
                return by_code_map[c]
        return {}

    if compiled.metric == "pnl_statement" and dims and dims[0] == "line_item":
        fy = (compiled.effective_period or {}).get("fy", "FY26")
        by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
        rev = _pick_n(by_code, "PL.REV_OPS", "gross_revenue_inr_cr").get("amount_cr")
        ti = _pick_n(by_code, "PL.TOTAL_INCOME", "total_income_inr_cr", "PL.REV_OPS", "gross_revenue_inr_cr").get("amount_cr")
        te = _pick_n(by_code, "PL.TOTAL_EXP", "total_expenses_inr_cr").get("amount_cr")
        pbt = _pick_n(by_code, "PL.PBT", "pbt_inr_cr").get("amount_cr")
        pat = _pick_n(by_code, "PL.PAT", "pat_inr_cr").get("amount_cr")
        return (
            f"For {fy}, ONGC's Schedule III Revenue from Operations is {fmt_num(rev, 'inr_cr')}, "
            f"Total Income is {fmt_num(ti, 'inr_cr')}, Total Expenses are {fmt_num(te, 'inr_cr')}, "
            f"Profit Before Tax is {fmt_num(pbt, 'inr_cr')}, and Profit for the Year (PAT) is {fmt_num(pat, 'inr_cr')}. "
            f"The complete Schedule III P&L statement is on screen."
        )
    if compiled.metric == "balance_sheet" and dims and dims[0] == "line_item":
        fy = (compiled.effective_period or {}).get("fy", "FY26")
        by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
        ta = _pick_n(by_code, "BS.TOTAL_ASSETS", "total_assets_inr_cr").get("amount_cr")
        nca = _pick_n(by_code, "BS.ASSETS.NON_CURRENT.TOTAL", "non_current_assets_inr_cr").get("amount_cr")
        ca = _pick_n(by_code, "BS.ASSETS.CURRENT.TOTAL", "current_assets_inr_cr").get("amount_cr")
        nw = _pick_n(by_code, "BS.EQUITY.TOTAL", "net_worth_inr_cr").get("amount_cr")
        ncl = _pick_n(by_code, "BS.LIAB.NON_CURRENT.TOTAL", "non_current_liabilities_inr_cr").get("amount_cr")
        cl = _pick_n(by_code, "BS.LIAB.CURRENT.TOTAL", "current_liabilities_inr_cr").get("amount_cr")
        return (
            f"As of 31 March {fy}, ONGC's Schedule III Total Assets stand at {fmt_num(ta, 'inr_cr')} "
            f"(Non-Current Assets {fmt_num(nca, 'inr_cr')} and Current Assets {fmt_num(ca, 'inr_cr')}), "
            f"balanced by Total Equity of {fmt_num(nw, 'inr_cr')}, Non-Current Liabilities of {fmt_num(ncl, 'inr_cr')}, "
            f"and Current Liabilities of {fmt_num(cl, 'inr_cr')}. The complete Schedule III Balance Sheet is on screen."
        )
    if compiled.metric == "cash_flow_statement" and dims and dims[0] == "line_item":
        fy = (compiled.effective_period or {}).get("fy", "FY26")
        by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
        ocf = _pick_n(by_code, "CF.CFO", "operating_cash_flow_inr_cr").get("amount_cr")
        icf = _pick_n(by_code, "CF.CFI", "investing_cash_flow_inr_cr").get("amount_cr")
        fcf_act = _pick_n(by_code, "CF.CFF", "financing_cash_flow_inr_cr").get("amount_cr")
        cls_c = _pick_n(by_code, "CF.CCE_CLOSE", "closing_cash_inr_cr").get("amount_cr")
        return (
            f"In {fy}, ONGC generated Net Cash from Operating Activities (OCF) of {fmt_num(ocf, 'inr_cr')}, "
            f"used {fmt_num(icf, 'inr_cr')} in Investing Activities and {fmt_num(fcf_act, 'inr_cr')} in Financing Activities, "
            f"with Closing Cash & Cash Equivalents of {fmt_num(cls_c, 'inr_cr')}. "
            f"The complete Ind-AS 7 Cash Flow Statement is on screen."
        )
    if compiled.metric == "financial_ratios" and dims and dims[0] == "line_item":
        fy = (compiled.effective_period or {}).get("fy", "FY26")
        by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
        ebm = _pick_n(by_code, "RATIO.PBIDT_MARGIN_PCT", "ebitda_margin_pct").get("value")
        pm = _pick_n(by_code, "RATIO.PAT_MARGIN_PCT", "pat_margin_pct").get("value")
        roce = _pick_n(by_code, "RATIO.ROCE", "standalone_roce_pct").get("value")
        roe = _pick_n(by_code, "RATIO.ROE_INCL_EXC", "roe_pct").get("value")
        de = _pick_n(by_code, "RATIO.DEBT_EQUITY", "debt_to_equity_ratio").get("value")
        eps = _pick_n(by_code, "PL.EPS_BASIC", "RATIO.EPS", "eps_basic_inr").get("value")
        return (
            f"For {fy}, ONGC's PBIDT Margin is {fmt_num(ebm, 'pct')}, Standalone PAT Margin is {fmt_num(pm, 'pct')}, "
            f"Standalone ROCE is {fmt_num(roce, 'pct')}, Return on Equity (ROE) is {fmt_num(roe, 'pct')}, "
            f"Debt-to-Equity is {de}x, and Basic EPS is ₹{eps}/share. The complete ratio scorecard is on screen."
        )

    if compiled.metric in ("pnl_statement", "balance_sheet", "cash_flow_statement") and "line_code" in (columns or []):
        fys = sorted(list({str(r["fiscal_year"]) for r in rows if "fiscal_year" in r}), reverse=True)
        if not fys:
            fy = (compiled.effective_period or {}).get("fy", "FY26")
            fys = [fy]
        
        if len(fys) > 1:
            lo, hi = fys[-1], fys[0]
            def _get_val(cd, yr):
                for r in rows:
                    if str(r.get("line_code")) == cd and str(r.get("fiscal_year")) == yr:
                        return r.get("amount_cr") or r.get("value_inr_cr")
                return None
            
            if compiled.metric == "pnl_statement":
                rev_hi, rev_lo = _get_val("PL.REV_OPS", hi), _get_val("PL.REV_OPS", lo)
                pat_hi, pat_lo = _get_val("PL.PAT", hi), _get_val("PL.PAT", lo)
                return f"Between {lo} and {hi}, ONGC's Revenue from Operations moved from ₹{rev_lo:,.1f} cr to ₹{rev_hi:,.1f} cr, and Standalone PAT from ₹{pat_lo:,.1f} cr to ₹{pat_hi:,.1f} cr. The complete Schedule III P&L trend is on screen."
            elif compiled.metric == "balance_sheet":
                ta_hi, ta_lo = _get_val("BS.TOTAL_ASSETS", hi), _get_val("BS.TOTAL_ASSETS", lo)
                return f"Between {lo} and {hi}, ONGC's Total Assets moved from ₹{ta_lo:,.1f} cr to ₹{ta_hi:,.1f} cr. The complete Balance Sheet trend is on screen."
            elif compiled.metric == "cash_flow_statement":
                cfo_hi, cfo_lo = _get_val("CF.CFO", hi), _get_val("CF.CFO", lo)
                return f"Between {lo} and {hi}, ONGC's Operating Cash Flow moved from ₹{cfo_lo:,.1f} cr to ₹{cfo_hi:,.1f} cr. The complete Cash Flow trend is on screen."


    if compiled.metric in ("pnl_statement", "balance_sheet", "cash_flow_statement") and "line_code" in (columns or []):
        fys = sorted(list({str(r["fiscal_year"]) for r in rows if "fiscal_year" in r}), reverse=True)
        if not fys:
            fy = (compiled.effective_period or {}).get("fy", "FY26")
            fys = [fy]
        
        if len(fys) > 1:
            lo, hi = fys[-1], fys[0]
            def _get_val(cd, yr):
                for r in rows:
                    if str(r.get("line_code")) == cd and str(r.get("fiscal_year")) == yr:
                        return r.get("amount_cr") or r.get("value_inr_cr")
                return None
            
            if compiled.metric == "pnl_statement":
                rev_hi, rev_lo = _get_val("PL.REV_OPS", hi), _get_val("PL.REV_OPS", lo)
                pat_hi, pat_lo = _get_val("PL.PAT", hi), _get_val("PL.PAT", lo)
                return f"Between {lo} and {hi}, ONGC's Revenue from Operations moved from ₹{rev_lo:,.1f} cr to ₹{rev_hi:,.1f} cr, and Standalone PAT from ₹{pat_lo:,.1f} cr to ₹{pat_hi:,.1f} cr. The complete Schedule III P&L trend is on screen."
            elif compiled.metric == "balance_sheet":
                ta_hi, ta_lo = _get_val("BS.TOTAL_ASSETS", hi), _get_val("BS.TOTAL_ASSETS", lo)
                return f"Between {lo} and {hi}, ONGC's Total Assets moved from ₹{ta_lo:,.1f} cr to ₹{ta_hi:,.1f} cr. The complete Balance Sheet trend is on screen."
            elif compiled.metric == "cash_flow_statement":
                cfo_hi, cfo_lo = _get_val("CF.CFO", hi), _get_val("CF.CFO", lo)
                return f"Between {lo} and {hi}, ONGC's Operating Cash Flow moved from ₹{cfo_lo:,.1f} cr to ₹{cfo_hi:,.1f} cr. The complete Cash Flow trend is on screen."

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
        total = n_total if n_total is not None else sum(_num(r.get(val)) for r in rows)
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
