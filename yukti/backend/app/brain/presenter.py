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
        out.append("As of 19-Oct-2026")
    return out


def build_visual(spec: QuerySpec, compiled: CompiledQuery, columns: List[str], rows: List[Dict[str, Any]],
                 chart_kind: Optional[str], title: str, subtitle: str, mode: str,
                 n_total: Optional[int] = None,
                 breakdown: Optional[Tuple[List[str], List[Dict[str, Any]]]] = None) -> Dict[str, Any]:
    unit = CHART_UNIT.get(compiled.unit)
    unit_word = UNIT_WORDS.get(compiled.unit, "")
    cap = 2000 if compiled.grain == "row" else 200   # rosters ship whole (UI virtualises, U5.2)
    table = {"columns": columns, "rows": rows[:cap], "total_rows": n_total if n_total is not None else len(rows)}
    vis: Dict[str, Any] = {"type": "table", "mode": mode, "title": title, "subtitle": subtitle, "table": table}
    if not rows:
        return vis
    if compiled.grain == "row":
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
    if compiled.metric == "pnl_statement" and dims and dims[0] == "line_item":
        # Single-FY Schedule III Statement of Profit & Loss
        fy = (compiled.effective_period or {}).get("fy", "FY26")
        by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
        rev_r = by_code.get("gross_revenue_inr_cr", {})
        eb_r = by_code.get("ebitda_inr_cr", {})
        pat_r = by_code.get("pat_inr_cr", {})
        cpat_r = by_code.get("consolidated_pat_inr_cr", {})
        vis["kpis"] = [
            {
                "label": f"Revenue from Ops ({fy})",
                "value": rev_r.get("amount_cr"),
                "unit": "₹ crore",
                "delta": f"{rev_r.get('yoy_change_pct'):+.1f}% vs prior FY" if isinstance(rev_r.get("yoy_change_pct"), (int, float)) else "",
            },
            {
                "label": f"Standalone EBITDA ({fy})",
                "value": eb_r.get("amount_cr"),
                "unit": "₹ crore",
                "delta": f"{eb_r.get('pct_of_revenue'):.1f}% EBITDA margin" if isinstance(eb_r.get("pct_of_revenue"), (int, float)) else "",
            },
            {
                "label": f"Standalone PAT ({fy})",
                "value": pat_r.get("amount_cr"),
                "unit": "₹ crore",
                "delta": f"{pat_r.get('yoy_change_pct'):+.1f}% YoY · {pat_r.get('pct_of_revenue'):.1f}% margin" if isinstance(pat_r.get("yoy_change_pct"), (int, float)) else "",
            },
            {
                "label": "Consolidated PAT (Group)",  # P0.3: no market-data label
                "value": cpat_r.get("amount_cr"),
                "unit": "₹ crore",
                "delta": f"{cpat_r.get('yoy_change_pct'):+.1f}% YoY (Group)" if isinstance(cpat_r.get("yoy_change_pct"), (int, float)) else "Group Net Income",
            },
        ]
        # 7 clean display columns + hidden line_code so frontend re-plot can classify statement lines
        disp_cols = ["line_item", "note_ref", "amount_cr", "prior_fy_cr", "yoy_delta_cr", "yoy_change_pct", "pct_of_revenue", "line_code"]
        disp_rows = [{k: r.get(k) for k in disp_cols} for r in rows]
        vis["table"] = {"columns": disp_cols, "rows": disp_rows, "total_rows": len(disp_rows)}
        # P4.1 (SPEC-09 §4.3): build the signed P&L waterfall bridge from statement lines (no EBITDA plug)
        from app.brain.bridge import BridgeOk, bridge, bridge_chart_rows

        b_res = bridge(rows, period=fy)
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
            # Table-First rule: default to structured statement table unless a chart (e.g., waterfall) was explicitly requested
            vis["type"] = "chart" if (chart_kind and chart_kind not in ("kpi", "table")) else "table"
        else:
            # M3 (SPEC-09 §4.3 step 6): on BridgeError, keep statement table, leave vis["chart"] unset, attach BridgeError copy
            vis.pop("chart", None)
            vis["type"] = "table"
            if chart_kind and chart_kind not in ("kpi", "table"):
                vis["note"] = b_res.message("en")
                vis["note_hi"] = b_res.message("hi")
                vis["bridge_error"] = {"code": b_res.code, "reason": b_res.reason}
        return vis

    if compiled.metric == "balance_sheet" and dims and dims[0] == "line_item":
        fy = (compiled.effective_period or {}).get("fy", "FY26")
        by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
        ta_r = by_code.get("total_assets_inr_cr", {})
        nw_r = by_code.get("net_worth_inr_cr", {})
        ltd_r = by_code.get("long_term_debt_inr_cr", {})
        cash_r = by_code.get("cash_and_bank_inr_cr", {})
        vis["kpis"] = [
            {
                "label": f"Total Assets ({fy})",
                "value": ta_r.get("amount_cr"),
                "unit": "₹ crore",
                "delta": f"{ta_r.get('yoy_change_pct'):+.1f}% vs prior FY" if isinstance(ta_r.get("yoy_change_pct"), (int, float)) else "Assets = Equity + Liab",
            },
            {
                "label": f"Standalone Net Worth ({fy})",
                "value": nw_r.get("amount_cr"),
                "unit": "₹ crore",
                "delta": f"{nw_r.get('pct_of_assets'):.1f}% of Total Assets" if isinstance(nw_r.get("pct_of_assets"), (int, float)) else "",
            },
            {
                "label": f"Long-Term Borrowings ({fy})",
                "value": ltd_r.get("amount_cr"),
                "unit": "₹ crore",
                "delta": f"{ltd_r.get('yoy_change_pct'):+.1f}% YoY" if isinstance(ltd_r.get("yoy_change_pct"), (int, float)) else "Note 21 Bonds",
            },
            {
                "label": f"Cash & Bank Balances ({fy})",
                "value": cash_r.get("amount_cr"),
                "unit": "₹ crore",
                "delta": f"{cash_r.get('yoy_change_pct'):+.1f}% YoY (Net Cash Positive)" if isinstance(cash_r.get("yoy_change_pct"), (int, float)) else "Note 15/16",
            },
        ]
        disp_cols = ["line_item", "note_ref", "section", "amount_cr", "prior_fy_cr", "yoy_change_pct", "pct_of_assets", "line_code"]
        disp_rows = [{k: r.get(k) for k in disp_cols} for r in rows]
        vis["table"] = {"columns": disp_cols, "rows": disp_rows, "total_rows": len(disp_rows)}
        bs_chart_codes = [
            ("non_current_assets_inr_cr", "Non-Current Assets"),
            ("current_assets_inr_cr", "Current Assets"),
            ("total_assets_inr_cr", "Total Assets"),
            ("net_worth_inr_cr", "Standalone Net Worth"),
            ("non_current_liabilities_inr_cr", "Non-Current Liabilities"),
            ("current_liabilities_inr_cr", "Current Liabilities"),
        ]
        bs_chart_rows = [
            {"bs_head": lbl, "amount_cr": by_code[c].get("amount_cr"), "prior_fy_cr": by_code[c].get("prior_fy_cr")}
            for c, lbl in bs_chart_codes if c in by_code
        ]
        ck = chart_kind if chart_kind and chart_kind not in ("kpi", "table") else "bar"
        vis["chart"] = build_chart_spec(kind=ck, columns=["bs_head", "amount_cr", "prior_fy_cr"], rows=bs_chart_rows, title=title, unit="₹ Cr")
        vis["type"] = "chart" if (chart_kind and chart_kind not in ("kpi", "table")) else "table"
        return vis

    if compiled.metric == "cash_flow_statement" and dims and dims[0] == "line_item":
        fy = (compiled.effective_period or {}).get("fy", "FY26")
        by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
        ocf_r = by_code.get("operating_cash_flow_inr_cr", {})
        icf_r = by_code.get("investing_cash_flow_inr_cr", {})
        fcf_r = by_code.get("free_cash_flow_inr_cr", {})
        cls_r = by_code.get("closing_cash_inr_cr", {})
        vis["kpis"] = [
            {
                "label": f"Operating Cash Flow ({fy})",
                "value": ocf_r.get("amount_cr"),
                "unit": "₹ crore",
                "delta": f"{ocf_r.get('yoy_change_pct'):+.1f}% vs prior FY" if isinstance(ocf_r.get("yoy_change_pct"), (int, float)) else "Ind-AS 7 OCF",
            },
            {
                "label": f"Investing Cash Flow ({fy})",
                "value": icf_r.get("amount_cr"),
                "unit": "₹ crore",
                "delta": "Capex + JVs net of Dividends",
            },
            {
                "label": f"Free Cash Flow ({fy})",
                "value": fcf_r.get("amount_cr"),
                "unit": "₹ crore",
                "delta": f"{fcf_r.get('pct_of_ocf'):.1f}% of OCF" if isinstance(fcf_r.get("pct_of_ocf"), (int, float)) else "OCF − Total Capex",
            },
            {
                "label": f"Closing Cash & Bank ({fy})",
                "value": cls_r.get("amount_cr"),
                "unit": "₹ crore",
                "delta": f"{cls_r.get('yoy_change_pct'):+.1f}% vs prior FY" if isinstance(cls_r.get("yoy_change_pct"), (int, float)) else "Note 15/16",
            },
        ]
        disp_cols = ["line_item", "note_ref", "section", "amount_cr", "prior_fy_cr", "yoy_delta_cr", "pct_of_ocf", "line_code"]
        disp_rows = [{k: r.get(k) for k in disp_cols} for r in rows]
        vis["table"] = {"columns": disp_cols, "rows": disp_rows, "total_rows": len(disp_rows)}
        pbt_v = _num(by_code.get("pbt_inr_cr", {}).get("amount_cr"))
        nc_wc_v = round(
            _num(by_code.get("non_cash_adjustments_cf_inr_cr", {}).get("amount_cr"))
            + _num(by_code.get("working_capital_change_cf_inr_cr", {}).get("amount_cr")),
            2,
        )
        tax_p_v = -abs(_num(by_code.get("income_tax_paid_cf_inr_cr", {}).get("amount_cr")))
        ocf_v = _num(by_code.get("operating_cash_flow_inr_cr", {}).get("amount_cr"))
        icf_v = _num(by_code.get("investing_cash_flow_inr_cr", {}).get("amount_cr"))
        fcf_act_v = _num(by_code.get("financing_cash_flow_inr_cr", {}).get("amount_cr"))
        net_chg_v = _num(by_code.get("net_cash_change_inr_cr", {}).get("amount_cr"))
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
        vis["type"] = "chart" if (chart_kind and chart_kind not in ("kpi", "table")) else "table"
        return vis

    if compiled.metric == "financial_ratios" and dims and dims[0] == "line_item":
        fy = (compiled.effective_period or {}).get("fy", "FY26")
        by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
        ebm_r = by_code.get("ebitda_margin_pct", {})
        roce_r = by_code.get("standalone_roce_pct", {})
        roe_r = by_code.get("roe_pct", {})
        de_r = by_code.get("debt_to_equity_ratio", {})
        vis["kpis"] = [
            {"label": f"EBITDA Margin ({fy})", "value": ebm_r.get("value"), "unit": "%", "delta": "Operating Profitability"},
            {"label": f"Standalone ROCE ({fy})", "value": roce_r.get("value"), "unit": "%", "delta": "Return on Capital Employed"},
            {"label": f"Return on Equity ({fy})", "value": roe_r.get("value"), "unit": "%", "delta": "PAT / Net Worth"},
            {"label": f"Debt-to-Equity ({fy})", "value": de_r.get("value"), "unit": "x", "delta": "Net Cash Positive Balance Sheet"},
        ]
        disp_cols = ["line_item", "category", "unit", "value", "prior_fy_value", "yoy_delta", "formula", "line_code"]
        disp_rows = [{k: r.get(k) for k in disp_cols} for r in rows]
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
            ck = chart_kind if chart_kind and chart_kind not in ("kpi", "table") else (
                "line" if bd_dim in ("fiscal_year", "fy") else select_chart_kind(columns=[bd_dim, bd_val], rows=bd_rows)
            )
            if ck in ("kpi", "table"):
                ck = "hbar"
            vis["type"] = "chart"
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
    if compiled.metric == "pnl_statement" and dims and dims[0] == "line_item":
        fy = (compiled.effective_period or {}).get("fy", "FY26")
        by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
        rev = by_code.get("gross_revenue_inr_cr", {}).get("amount_cr")
        lev = by_code.get("statutory_levies_total_inr_cr", {}).get("amount_cr")
        eb = by_code.get("ebitda_inr_cr", {}).get("amount_cr")
        pbt = by_code.get("pbt_inr_cr", {}).get("amount_cr")
        pat = by_code.get("pat_inr_cr", {}).get("amount_cr")
        cpat = by_code.get("consolidated_pat_inr_cr", {}).get("amount_cr")
        return (
            f"For {fy}, ONGC's Schedule III Revenue from Operations is {fmt_num(rev, 'inr_cr')}, "
            f"Statutory Levies are {fmt_num(lev, 'inr_cr')}, Standalone EBITDA is {fmt_num(eb, 'inr_cr')}, "
            f"Profit Before Tax is {fmt_num(pbt, 'inr_cr')}, Standalone PAT is {fmt_num(pat, 'inr_cr')}, "
            f"and Consolidated Group PAT is {fmt_num(cpat, 'inr_cr')}. "
            f"The complete 23-line Schedule III P&L statement is on screen."
        )
    if compiled.metric == "balance_sheet" and dims and dims[0] == "line_item":
        fy = (compiled.effective_period or {}).get("fy", "FY26")
        by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
        ta = by_code.get("total_assets_inr_cr", {}).get("amount_cr")
        nca = by_code.get("non_current_assets_inr_cr", {}).get("amount_cr")
        ca = by_code.get("current_assets_inr_cr", {}).get("amount_cr")
        nw = by_code.get("net_worth_inr_cr", {}).get("amount_cr")
        ncl = by_code.get("non_current_liabilities_inr_cr", {}).get("amount_cr")
        cl = by_code.get("current_liabilities_inr_cr", {}).get("amount_cr")
        return (
            f"As of 31 March {fy}, ONGC's Schedule III Total Assets stand at {fmt_num(ta, 'inr_cr')} "
            f"(Non-Current Assets {fmt_num(nca, 'inr_cr')} and Current Assets {fmt_num(ca, 'inr_cr')}), "
            f"balanced by Standalone Net Worth of {fmt_num(nw, 'inr_cr')}, Non-Current Liabilities of {fmt_num(ncl, 'inr_cr')}, "
            f"and Current Liabilities of {fmt_num(cl, 'inr_cr')}. The complete 24-line Schedule III Balance Sheet is on screen."
        )
    if compiled.metric == "cash_flow_statement" and dims and dims[0] == "line_item":
        fy = (compiled.effective_period or {}).get("fy", "FY26")
        by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
        ocf = by_code.get("operating_cash_flow_inr_cr", {}).get("amount_cr")
        icf = by_code.get("investing_cash_flow_inr_cr", {}).get("amount_cr")
        fcf_act = by_code.get("financing_cash_flow_inr_cr", {}).get("amount_cr")
        fcf = by_code.get("free_cash_flow_inr_cr", {}).get("amount_cr")
        cls_c = by_code.get("closing_cash_inr_cr", {}).get("amount_cr")
        return (
            f"In {fy}, ONGC generated Net Cash from Operating Activities (OCF) of {fmt_num(ocf, 'inr_cr')}, "
            f"used {fmt_num(icf, 'inr_cr')} in Investing Activities and {fmt_num(fcf_act, 'inr_cr')} in Financing Activities, "
            f"delivering Free Cash Flow (FCF) of {fmt_num(fcf, 'inr_cr')} and Closing Cash & Bank Balances of {fmt_num(cls_c, 'inr_cr')}. "
            f"The complete 18-line Ind-AS 7 Cash Flow Statement is on screen."
        )
    if compiled.metric == "financial_ratios" and dims and dims[0] == "line_item":
        fy = (compiled.effective_period or {}).get("fy", "FY26")
        by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
        ebm = by_code.get("ebitda_margin_pct", {}).get("value")
        pm = by_code.get("pat_margin_pct", {}).get("value")
        roce = by_code.get("standalone_roce_pct", {}).get("value")
        roe = by_code.get("roe_pct", {}).get("value")
        de = by_code.get("debt_to_equity_ratio", {}).get("value")
        eps = by_code.get("eps_basic_inr", {}).get("value")
        return (
            f"For {fy}, ONGC's EBITDA Margin is {fmt_num(ebm, 'pct')}, Standalone PAT Margin is {fmt_num(pm, 'pct')}, "
            f"Standalone ROCE is {fmt_num(roce, 'pct')}, Return on Equity (ROE) is {fmt_num(roe, 'pct')}, "
            f"Debt-to-Equity is {de}x, and Basic EPS is ₹{eps}/share. The complete 18-ratio scorecard is on screen."
        )
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
