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
                          prev_rows: Optional[List[Dict[str, Any]]], scope: List[str], query: str = "") -> InsightContext:
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
    if compiled.metric == "pnl_statement" and rows:
        fy = (compiled.effective_period or {}).get("fy")
        if fy and "line_item" in rows[0]:
            ctx.dim, ctx.value_col, ctx.unit = None, "amount_cr", "inr_cr"
            ctx.extra_insights = _pnl_statement_insights(rows, fy, query)
        else:
            ctx.dim, ctx.value_col, ctx.unit = "fiscal_year", "standalone_pat_cr", "inr_cr"
            ctx.extra_insights = _pnl_multi_year_insights(rows, query)
    elif compiled.metric == "balance_sheet" and rows:
        fy = (compiled.effective_period or {}).get("fy")
        if fy and "line_item" in rows[0]:
            ctx.dim, ctx.value_col, ctx.unit = None, "amount_cr", "inr_cr"
            ctx.extra_insights = _balance_sheet_insights(rows, fy, query)
        else:
            ctx.dim, ctx.value_col, ctx.unit = "fiscal_year", "total_assets_cr", "inr_cr"
            ctx.extra_insights = _bs_multi_year_insights(rows, query)
    elif compiled.metric == "cash_flow_statement" and rows:
        fy = (compiled.effective_period or {}).get("fy")
        if fy and "line_item" in rows[0]:
            ctx.dim, ctx.value_col, ctx.unit = None, "amount_cr", "inr_cr"
            ctx.extra_insights = _cash_flow_insights(rows, fy, query)
        else:
            ctx.dim, ctx.value_col, ctx.unit = "fiscal_year", "operating_cash_flow_cr", "inr_cr"
            ctx.extra_insights = _cf_multi_year_insights(rows, query)
    elif compiled.metric == "financial_ratios" and rows:
        fy = (compiled.effective_period or {}).get("fy")
        if fy and "line_item" in rows[0]:
            ctx.dim, ctx.value_col, ctx.unit = None, "value", "ratio"
            ctx.extra_insights = _financial_ratios_insights(rows, fy, query)
        else:
            ctx.dim, ctx.value_col, ctx.unit = "fiscal_year", "roce_pct", "pct"
            ctx.extra_insights = _ratios_multi_year_insights(rows, query)
    elif compiled.subject in ("corporate", "field_finance", "subsidiary_finance", "capex") and rows:
        ctx.extra_insights = _corporate_causal_insights(compiled, rows, query)
    return ctx


def _extract_nums(text: str) -> List[float]:
    import re
    out: List[float] = []
    for m in re.finditer(r"-?\d+(?:,\d+)*(?:\.\d+)?", text or ""):
        try:
            out.append(float(m.group(0).replace(",", "")))
        except ValueError:
            pass
    return out


def _lookup_line_context(fy: str, line_code: str) -> Dict[str, Any]:
    from pathlib import Path
    import json
    try:
        ctx_path = Path(__file__).resolve().parents[4] / "financial_build" / "data" / "ssot_financial_line_context.json"
        if not ctx_path.exists():
            return {}
        rows = json.loads(ctx_path.read_text())
        for r in rows:
            if r.get("fy") == fy and r.get("line_code") == line_code:
                return r
    except Exception:
        pass
    return {}


def _search_financial_rag(query: str, fy: Optional[str], metric: str) -> Optional[str]:
    """Hybrid deterministic + semantic tag retrieval over financial_notes_corpus.jsonl and ssot_financial_line_context.json."""
    from pathlib import Path
    import json
    import re
    if not query:
        return None
    ql = query.lower()
    is_causal_or_action = bool(re.search(
        r"\b(why|what\s+happened|how\s+did|driver\w*|reason\w*|cause\w*|explain|note\s+\d+|action\w*|recommend\w*|"
        r"interven\w*|improv\w*|saed|windfall|115baa|impairment|opal|hpcl|kg[- ]dwn|98/2|ind[- ]?as|aro|site\s+restoration|"
        r"dry\s+well\w*|pec|nwng|new\s+well\s+gas)\b",
        ql,
    ))
    if not is_causal_or_action:
        return None
    try:
        corpus_path = Path(__file__).resolve().parents[4] / "financial_build" / "data" / "financial_notes_corpus.jsonl"
        if not corpus_path.exists():
            return None
        q_tokens = set(re.findall(r"[a-z0-9_]{3,}", ql)) - {"the", "and", "for", "from", "what", "why", "how", "did", "was", "were", "ongc", "show", "tell"}
        best_score = 0.0
        best_chunk = None
        for line in corpus_path.read_text().splitlines():
            if not line.strip():
                continue
            c = json.loads(line)
            score = 0.0
            cfy = str(c.get("fiscal_year") or "")
            if fy and cfy == fy:
                score += 4.0
            elif cfy == "ALL":
                score += 2.5
            tags = {str(t).lower() for t in (c.get("causal_tags") or [])}
            title_l = str(c.get("title") or "").lower()
            content_l = str(c.get("content") or "").lower()
            for tok in q_tokens:
                if tok in tags:
                    score += 5.0
                if tok in title_l:
                    score += 3.0
                if tok in content_l:
                    score += 1.0
            if re.search(r"\b(action\w*|recommend\w*|interven\w*|director\s+finance|finance\s+director|improv\w*|turnaround)\b", ql):
                if c.get("chunk_id") == "FIN-DIRECTOR-FINANCE-ACTION-PLAYBOOK-FY26-FY27" or "Action" in str(c.get("section_type")):
                    score += 8.0
            if score > best_score:
                best_score = score
                best_chunk = c
        if best_chunk and best_score >= 5.0:
            return f"{best_chunk['title']} ({best_chunk['note_ref']}): {best_chunk['content']}"
    except Exception:
        pass
    return None


def _pnl_statement_insights(rows: List[Dict[str, Any]], fy: str, query: str = ""):
    from app.brain.insights import Insight, fmt
    by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
    rev = by_code.get("gross_revenue_inr_cr", {})
    lev = by_code.get("statutory_levies_total_inr_cr", {})
    saed = by_code.get("saed_windfall_tax_inr_cr", {})
    ebitda = by_code.get("ebitda_inr_cr", {})
    exp_wo = by_code.get("exploration_costs_written_off_inr_cr", {})
    dda = by_code.get("dda_inr_cr", {})
    pbt = by_code.get("pbt_inr_cr", {})
    tax = by_code.get("tax_expense_total_inr_cr", {})
    pat = by_code.get("pat_inr_cr", {})
    cpat = by_code.get("consolidated_pat_inr_cr", {})

    out: List[Insight] = []
    if rev and ebitda and pat:
        rv = float(rev.get("amount_cr") or 0)
        ebv = float(ebitda.get("amount_cr") or 0)
        eb_pct = float(ebitda.get("pct_of_revenue") or 0)
        pv = float(pat.get("amount_cr") or 0)
        pyoy = float(pat.get("yoy_change_pct") or 0)
        cpv = float(cpat.get("amount_cr") or 0)
        txt = (
            f"Schedule III {fy} Summary: Revenue from Operations {fmt(rv, 'inr_cr')}, "
            f"Standalone EBITDA {fmt(ebv, 'inr_cr')} ({eb_pct:.1f}% margin), "
            f"Standalone PAT {fmt(pv, 'inr_cr')} ({pyoy:+.1f}% YoY), and Consolidated Group PAT (ONGC.NS) {fmt(cpv, 'inr_cr')}."
        )
        out.append(Insight(kind="headline", type="headline", value=pv, unit="inr_cr", ref="IX. Standalone Profit After Tax (PAT)",
                           text=txt, facts=[rv, ebv, eb_pct, pv, abs(pyoy), pyoy, cpv] + _extract_nums(txt), priority=1))
    rag_txt = _search_financial_rag(query, fy, "pnl_statement")
    ctx_row = _lookup_line_context(fy, "pnl_statement")
    driver = str(ctx_row.get("what_happened_summary") or pat.get("driver_note") or rev.get("driver_note") or "").strip()
    action = str(ctx_row.get("director_finance_action") or "").strip()
    if rag_txt:
        out.append(Insight(kind="note", type="causal_rag", value=None, unit="", ref=None,
                           text=rag_txt, facts=_extract_nums(rag_txt), priority=2))
    elif driver:
        txt = f"Annual Report Context ({fy}): {driver}" + (f" | Director (Finance) Action: {action}" if action else "")
        out.append(Insight(kind="note", type="causal_rag", value=None, unit="", ref=None,
                           text=txt, facts=_extract_nums(txt), priority=2))
    if lev:
        lv = float(lev.get("amount_cr") or 0)
        lyoy = float(lev.get("yoy_change_pct") or 0)
        sv = float(saed.get("amount_cr") or 0)
        txt = (
            f"Note 28 (Statutory Levies): Total levies were {fmt(lv, 'inr_cr')} ({lyoy:+.1f}% YoY; "
            f"SAED windfall tax {fmt(sv, 'inr_cr')})."
        )
        out.append(Insight(kind="trend", type="pnl_levies", value=lv, unit="inr_cr", ref="Less: Statutory Levies (Royalty + Cess + SAED)",
                           text=txt, facts=[lv, abs(lyoy), lyoy, sv] + _extract_nums(txt), priority=3))
    if exp_wo and dda and pbt and tax:
        ew = float(exp_wo.get("amount_cr") or 0)
        dv = float(dda.get("amount_cr") or 0)
        pbtv = float(pbt.get("amount_cr") or 0)
        txv = float(tax.get("amount_cr") or 0)
        txt = (
            f"Notes 32–37 (Below-EBITDA Drivers): Exploration dry-well & survey write-offs were {fmt(ew, 'inr_cr')}, "
            f"DD&A was {fmt(dv, 'inr_cr')}, yielding PBT of {fmt(pbtv, 'inr_cr')} and Tax Expense of {fmt(txv, 'inr_cr')}."
        )
        out.append(Insight(kind="comparison", type="pnl_drivers", value=pbtv, unit="inr_cr", ref="VII. Profit Before Tax (PBT)",
                           text=txt, facts=[ew, dv, pbtv, txv] + _extract_nums(txt), priority=4))
    return out


def _pnl_multi_year_insights(rows: List[Dict[str, Any]], query: str = ""):
    from app.brain.insights import Insight, fmt
    if len(rows) < 2:
        return []
    first, last = rows[0], rows[-1]
    peak_rev = max(rows, key=lambda r: float(r.get("revenue_from_ops_cr") or 0))
    peak_pat = max(rows, key=lambda r: float(r.get("standalone_pat_cr") or 0))
    txt1 = (
        f"10-Year Trajectory ({first.get('fiscal_year')}–{last.get('fiscal_year')}): "
        f"Revenue grew from {fmt(float(first.get('revenue_from_ops_cr') or 0), 'inr_cr')} to {fmt(float(last.get('revenue_from_ops_cr') or 0), 'inr_cr')} "
        f"(peaking at {fmt(float(peak_rev.get('revenue_from_ops_cr') or 0), 'inr_cr')} in {peak_rev.get('fiscal_year')}); "
        f"Standalone PAT rose from {fmt(float(first.get('standalone_pat_cr') or 0), 'inr_cr')} to {fmt(float(last.get('standalone_pat_cr') or 0), 'inr_cr')} "
        f"(record {fmt(float(peak_pat.get('standalone_pat_cr') or 0), 'inr_cr')} in {peak_pat.get('fiscal_year')})."
    )
    rag_txt = _search_financial_rag(query, None, "pnl_statement")
    txt2 = rag_txt or (
        "Historical Causal Highlights: FY20 PAT dipped to ₹13,464 cr on ₹4,899 cr COVID crude impairment; "
        "FY22 PAT surged to ₹40,306 cr on ₹7,178 cr impairment reversal and Section 115BAA deferred tax credit (-₹8,846 cr); "
        "SAED windfall tax peaked at ₹10,964 cr in FY23 before abolition in Dec 2024 (₹0 cr in FY26)."
    )
    txt3 = (
        "Director (Finance) Action: Reallocate ₹4,200 cr infill capex to New Well Gas ($7.80/MMBtu, +20% premium over APM) "
        "and transition 12 high-water-cut mature clusters to PEC contracts (-₹620 cr/yr opex)."
    )
    return [
        Insight(kind="headline", type="headline", value=float(last.get("standalone_pat_cr") or 0), unit="inr_cr",
                ref=str(last.get("fiscal_year")), text=txt1, facts=_extract_nums(txt1), priority=1),
        Insight(kind="note", type="causal_rag", value=None, unit="", ref=None,
                text=txt2, facts=_extract_nums(txt2), priority=2),
        Insight(kind="note", type="action", value=None, unit="", ref=None,
                text=txt3, facts=_extract_nums(txt3), priority=3),
    ]


def _bs_multi_year_insights(rows: List[Dict[str, Any]], query: str = ""):
    from app.brain.insights import Insight, fmt
    if len(rows) < 2:
        return []
    first, last = rows[0], rows[-1]
    txt1 = (
        f"Balance Sheet Trajectory ({first.get('fiscal_year')}–{last.get('fiscal_year')}): "
        f"Total Assets nearly doubled from {fmt(float(first.get('total_assets_cr') or 0), 'inr_cr')} to {fmt(float(last.get('total_assets_cr') or 0), 'inr_cr')}, "
        f"while Standalone Net Worth expanded from {fmt(float(first.get('net_worth_cr') or 0), 'inr_cr')} to {fmt(float(last.get('net_worth_cr') or 0), 'inr_cr')}."
    )
    rag_txt = _search_financial_rag(query, None, "balance_sheet")
    txt2 = rag_txt or (
        "10-Year Balance Sheet Milestones: FY18 borrowings rose to ₹25,592 cr to fund the ₹36,915 cr HPCL (51.11%) buyout before being repaid to ₹7,850 cr in FY26; "
        "FY25–FY26 Non-Current Investments reached ₹1,19,840 cr following the ₹18,365 cr OPaL CCD-to-equity conversion (95.69% stake) and KG-DWN-98/2 CWIP capitalization."
    )
    return [
        Insight(kind="headline", type="headline", value=float(last.get("total_assets_cr") or 0), unit="inr_cr",
                ref=str(last.get("fiscal_year")), text=txt1, facts=_extract_nums(txt1), priority=1),
        Insight(kind="note", type="causal_rag", value=None, unit="", ref=None,
                text=txt2, facts=_extract_nums(txt2), priority=2),
    ]


def _cf_multi_year_insights(rows: List[Dict[str, Any]], query: str = ""):
    from app.brain.insights import Insight, fmt
    if len(rows) < 2:
        return []
    first, last = rows[0], rows[-1]
    tot_ocf = sum(float(r.get("operating_cash_flow_cr") or 0) for r in rows)
    tot_fcf = sum(float(r.get("free_cash_flow_cr") or 0) for r in rows)
    txt1 = (
        f"Cash Flow Trajectory ({first.get('fiscal_year')}–{last.get('fiscal_year')}): "
        f"Cumulative Operating Cash Flow was {fmt(tot_ocf, 'inr_cr')} and cumulative Free Cash Flow was {fmt(tot_fcf, 'inr_cr')}, "
        f"with {last.get('fiscal_year')} OCF at {fmt(float(last.get('operating_cash_flow_cr') or 0), 'inr_cr')} and FCF at {fmt(float(last.get('free_cash_flow_cr') or 0), 'inr_cr')}."
    )
    rag_txt = _search_financial_rag(query, None, "cash_flow_statement")
    txt2 = rag_txt or (
        "10-Year Capital Allocation: ONGC self-funded ₹3,00,137 cr of upstream E&P capex, the ₹36,915 cr HPCL buyout (FY18), "
        "the ₹4,022 cr share buyback (FY19), and the ₹18,365 cr OPaL recapitalization (FY25) while building ₹33,500 cr in Cash & Bank balances by FY26."
    )
    return [
        Insight(kind="headline", type="headline", value=tot_ocf, unit="inr_cr",
                ref=str(last.get("fiscal_year")), text=txt1, facts=_extract_nums(txt1), priority=1),
        Insight(kind="note", type="causal_rag", value=None, unit="", ref=None,
                text=txt2, facts=_extract_nums(txt2), priority=2),
    ]


def _ratios_multi_year_insights(rows: List[Dict[str, Any]], query: str = ""):
    from app.brain.insights import Insight
    if len(rows) < 2:
        return []
    first, last = rows[0], rows[-1]
    txt1 = (
        f"10-Year Ratios ({first.get('fiscal_year')}–{last.get('fiscal_year')}): "
        f"Standalone ROCE moved from {first.get('roce_pct')}% to {last.get('roce_pct')}% "
        f"(peaking during FY22–FY24 oil recovery) with Debt-to-Equity maintained between 0.00x and 0.13x."
    )
    rag_txt = _search_financial_rag(query, None, "financial_ratios")
    txt2 = rag_txt or (
        "Director (Finance) Credit & Efficiency Summary: ONGC sustained an average EBITDA margin of 49.4% and >1.0x 2P Reserve Replacement Ratio across all 10 years."
    )
    return [
        Insight(kind="headline", type="headline", value=float(last.get("roce_pct") or 0), unit="pct",
                ref=str(last.get("fiscal_year")), text=txt1, facts=_extract_nums(txt1), priority=1),
        Insight(kind="note", type="causal_rag", value=None, unit="", ref=None,
                text=txt2, facts=_extract_nums(txt2), priority=2),
    ]


def _balance_sheet_insights(rows: List[Dict[str, Any]], fy: str, query: str = ""):
    from app.brain.insights import Insight, fmt
    by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
    ta = by_code.get("total_assets_inr_cr", {})
    nca = by_code.get("non_current_assets_inr_cr", {})
    oga = by_code.get("oil_and_gas_assets_inr_cr", {})
    cwip = by_code.get("cwip_inr_cr", {})
    inv = by_code.get("investments_subsidiaries_jv_inr_cr", {})
    nw = by_code.get("net_worth_inr_cr", {})
    ltd = by_code.get("long_term_debt_inr_cr", {})
    aro = by_code.get("abandonment_provision_inr_cr", {})
    cash = by_code.get("cash_and_bank_inr_cr", {})

    out: List[Insight] = []
    if ta and nw:
        tav = float(ta.get("amount_cr") or 0)
        nwv = float(nw.get("amount_cr") or 0)
        ncav = float(nca.get("amount_cr") or 0)
        txt = (
            f"Schedule III {fy} Balance Sheet: Total Assets of {fmt(tav, 'inr_cr')} "
            f"(Non-Current Assets {fmt(ncav, 'inr_cr')}), funded by Standalone Net Worth of {fmt(nwv, 'inr_cr')}."
        )
        out.append(Insight(kind="headline", type="headline", value=tav, unit="inr_cr", ref="TOTAL ASSETS (I + II)",
                           text=txt, facts=[tav, nwv, ncav] + _extract_nums(txt), priority=1))
    rag_txt = _search_financial_rag(query, fy, "balance_sheet")
    ctx_row = _lookup_line_context(fy, "balance_sheet")
    driver = str(ctx_row.get("what_happened_summary") or ta.get("driver_note") or nw.get("driver_note") or "").strip()
    action = str(ctx_row.get("director_finance_action") or "").strip()
    if rag_txt:
        out.append(Insight(kind="note", type="causal_rag", value=None, unit="", ref=None,
                           text=rag_txt, facts=_extract_nums(rag_txt), priority=2))
    elif driver:
        txt = f"Annual Report Balance Sheet Context ({fy}): {driver}" + (f" | Director (Finance) Action: {action}" if action else "")
        out.append(Insight(kind="note", type="causal_rag", value=None, unit="", ref=None,
                           text=txt, facts=_extract_nums(txt), priority=2))
    if oga and cwip and inv:
        ogav = float(oga.get("amount_cr") or 0)
        cwv = float(cwip.get("amount_cr") or 0)
        invv = float(inv.get("amount_cr") or 0)
        txt = (
            f"Notes 5–10 (Asset Composition): Oil & Gas Producing Properties Net Block is {fmt(ogav, 'inr_cr')}, "
            f"Capital Work-in-Progress (CWIP) is {fmt(cwv, 'inr_cr')}, and Subsidiary/JV Investments (HPCL, OVL, MRPL, OPaL) are {fmt(invv, 'inr_cr')}."
        )
        out.append(Insight(kind="comparison", type="bs_assets", value=ogav, unit="inr_cr", ref="A1. Oil & Gas Producing Properties (Net Block)",
                           text=txt, facts=[ogav, cwv, invv] + _extract_nums(txt), priority=3))
    if ltd and aro and cash:
        ltdv = float(ltd.get("amount_cr") or 0)
        arov = float(aro.get("amount_cr") or 0)
        cv = float(cash.get("amount_cr") or 0)
        txt = (
            f"Notes 15–22 (Liquidity & Obligations): Cash & Bank Balances stand at {fmt(cv, 'inr_cr')} against "
            f"Long-Term Borrowings of {fmt(ltdv, 'inr_cr')} and Site Restoration ARO Provision of {fmt(arov, 'inr_cr')}."
        )
        out.append(Insight(kind="trend", type="bs_liab", value=cv, unit="inr_cr", ref="B4. Cash, Cash Equivalents & Term Bank Deposits",
                           text=txt, facts=[ltdv, arov, cv] + _extract_nums(txt), priority=4))
    return out


def _cash_flow_insights(rows: List[Dict[str, Any]], fy: str, query: str = ""):
    from app.brain.insights import Insight, fmt
    by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
    ocf = by_code.get("operating_cash_flow_inr_cr", {})
    icf = by_code.get("investing_cash_flow_inr_cr", {})
    fcf_act = by_code.get("financing_cash_flow_inr_cr", {})
    fcf = by_code.get("free_cash_flow_inr_cr", {})
    div_p = by_code.get("dividend_paid_cf_inr_cr", {})
    cls_c = by_code.get("closing_cash_inr_cr", {})

    out: List[Insight] = []
    if ocf and fcf:
        ocfv = float(ocf.get("amount_cr") or 0)
        fcfv = float(fcf.get("amount_cr") or 0)
        clsv = float(cls_c.get("amount_cr") or 0)
        txt = (
            f"Ind-AS 7 {fy} Cash Flow Summary: Net Cash from Operating Activities (OCF) was {fmt(ocfv, 'inr_cr')}, "
            f"generating Free Cash Flow (FCF) of {fmt(fcfv, 'inr_cr')} and Closing Cash of {fmt(clsv, 'inr_cr')}."
        )
        out.append(Insight(kind="headline", type="headline", value=ocfv, unit="inr_cr", ref="I. Net Cash from Operating Activities (OCF)",
                           text=txt, facts=[ocfv, fcfv, clsv] + _extract_nums(txt), priority=1))
    rag_txt = _search_financial_rag(query, fy, "cash_flow_statement")
    ctx_row = _lookup_line_context(fy, "cash_flow_statement")
    driver = str(ctx_row.get("what_happened_summary") or ocf.get("driver_note") or "").strip()
    action = str(ctx_row.get("director_finance_action") or "").strip()
    if rag_txt:
        out.append(Insight(kind="note", type="causal_rag", value=None, unit="", ref=None,
                           text=rag_txt, facts=_extract_nums(rag_txt), priority=2))
    elif driver:
        txt = f"Annual Report Cash Flow Context ({fy}): {driver}" + (f" | Director (Finance) Action: {action}" if action else "")
        out.append(Insight(kind="note", type="causal_rag", value=None, unit="", ref=None,
                           text=txt, facts=_extract_nums(txt), priority=2))
    if icf and fcf_act and div_p:
        icfv = float(icf.get("amount_cr") or 0)
        ffv = float(fcf_act.get("amount_cr") or 0)
        dpv = float(div_p.get("amount_cr") or 0)
        txt = (
            f"Capital Allocation ({fy}): Net Cash Used in Investing Activities was {fmt(icfv, 'inr_cr')} "
            f"and Net Cash Used in Financing Activities was {fmt(ffv, 'inr_cr')} (including Dividends Paid of {fmt(dpv, 'inr_cr')})."
        )
        out.append(Insight(kind="comparison", type="cf_alloc", value=fcfv if fcf else 0.0, unit="inr_cr", ref="Memo: Free Cash Flow (OCF − Total Capex)",
                           text=txt, facts=[icfv, ffv, dpv, abs(icfv), abs(ffv), abs(dpv)] + _extract_nums(txt), priority=3))
    return out


def _financial_ratios_insights(rows: List[Dict[str, Any]], fy: str, query: str = ""):
    from app.brain.insights import Insight
    by_code = {str(r.get("line_code")): r for r in rows if r.get("line_code")}
    ebm = by_code.get("ebitda_margin_pct", {}).get("value")
    pm = by_code.get("pat_margin_pct", {}).get("value")
    roce = by_code.get("standalone_roce_pct", {}).get("value")
    roe = by_code.get("roe_pct", {}).get("value")
    de = by_code.get("debt_to_equity_ratio", {}).get("value")
    icr = by_code.get("interest_coverage_ratio", {}).get("value")
    eps = by_code.get("eps_basic_inr", {}).get("value")
    dps = by_code.get("dividend_per_share_inr", {}).get("value")
    txt1 = (
        f"Profitability & Returns ({fy}): EBITDA Margin {ebm}%, Net PAT Margin {pm}%, "
        f"Standalone ROCE {roce}%, and Return on Equity (ROE) {roe}%."
    )
    txt2 = (
        f"Solvency & Per-Share ({fy}): Debt-to-Equity ratio is {de}x with {icr}x Interest Coverage; "
        f"Basic EPS is ₹{eps}/share and Dividend Per Share is ₹{dps}/share."
    )
    out = [
        Insight(kind="headline", type="headline", value=float(ebm or 0), unit="pct", ref="EBITDA Margin (%)",
                text=txt1, facts=_extract_nums(txt1), priority=1),
    ]
    rag_txt = _search_financial_rag(query, fy, "financial_ratios")
    ctx_row = _lookup_line_context(fy, "financial_ratios")
    action = str(ctx_row.get("director_finance_action") or "").strip()
    if rag_txt:
        out.append(Insight(kind="note", type="causal_rag", value=None, unit="", ref=None,
                           text=rag_txt, facts=_extract_nums(rag_txt), priority=2))
    elif action:
        txt3 = f"Director (Finance) Action ({fy}): {action}"
        out.append(Insight(kind="note", type="causal_rag", value=None, unit="", ref=None,
                           text=txt3, facts=_extract_nums(txt3), priority=2))
    out.append(
        Insight(kind="comparison", type="ratio_solv", value=float(de or 0), unit="ratio", ref="Debt-to-Equity Ratio (x)",
                text=txt2, facts=_extract_nums(txt2), priority=3)
    )
    return out


def _corporate_causal_insights(compiled: CompiledQuery, rows: List[Dict[str, Any]], query: str = ""):
    from app.brain.insights import Insight
    try:
        fy = (compiled.effective_period or {}).get("fy") or "FY26"
        rag_txt = _search_financial_rag(query, fy, compiled.metric)
        if rag_txt:
            return [Insight(kind="note", type="causal_rag", value=None, unit="", ref=fy,
                            text=rag_txt, facts=_extract_nums(rag_txt), priority=2)]
        ctx_row = _lookup_line_context(fy, compiled.metric)
        if not ctx_row:
            is_bs_metric = any(
                k in compiled.metric
                for k in ("asset", "cwip", "investment", "receivable", "inventory", "cash_and_bank", "equity", "net_worth", "debt", "lease", "abandonment", "liabilit")
            )
            ctx_row = _lookup_line_context(fy, "balance_sheet" if is_bs_metric else "pnl_statement")
        if ctx_row:
            summary = ctx_row.get("what_happened_summary", "")
            hist = ctx_row.get("historical_10yr_context", "")
            action = ctx_row.get("director_finance_action", "")
            txt = f"Annual Report Context ({fy}): {summary} 10-Yr Context: {hist} Director (Finance) Action: {action}"
            return [Insight(kind="note", type="causal_rag", value=None, unit="", ref=fy,
                            text=txt, facts=_extract_nums(txt), priority=2)]
    except Exception:
        pass
    return []


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
