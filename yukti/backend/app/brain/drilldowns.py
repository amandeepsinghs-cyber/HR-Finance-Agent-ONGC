"""Drill-down chip generator (B4.2, FEAT-011).

Every data answer gets 2–3 executable chips. A chip is a contract-v2 `drilldown`
`{label, question, spec_patch}`: the UI sends the `spec_patch` (plus the card's
`query_spec`) and the backend applies it deterministically (`apply_patch`), so a chip
never depends on the LLM understanding its label.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.brain.query_spec import QuerySpec
from app.brain.rbac import persona_class
from app.brain.semantic_model import get_semantic_model
from app.semantic.entities import get_entities
from app.semantic.normalize import last_complete_fy

# Default comparison partner for a work centre (peer of the same kind, data-derived fallback below).
_PEER = {"WC-DEL": "WC-MUM", "WC-MUM": "WC-DEL", "WC-DDN": "WC-DEL"}
_DIM_LABEL = {"grade": "By grade", "discipline": "By discipline", "wc": "By work centre", "asset": "By asset",
              "field": "By field", "fy": "Year by year"}


def _peer_wc(code: str) -> Optional[str]:
    if code in _PEER:
        return _PEER[code]
    ents = get_entities()
    a = ents.work_centres.get(code) or {}
    same = [c for c, b in ents.work_centres.items() if c != code and b.get("type") == a.get("type")
            and b.get("sector") == a.get("sector")]
    same = same or [c for c, b in ents.work_centres.items() if c != code and b.get("type") == a.get("type")]
    return same[0] if same else None


def make_drilldowns(spec: QuerySpec, persona: str, grain: str, max_n: int = 3) -> List[Dict[str, Any]]:
    sm = get_semantic_model()
    subject, metric, template = sm.resolve_metric(spec.metric)
    ents = get_entities()
    chips: List[Dict[str, Any]] = []

    def add(label: str, question: str, patch: Optional[Dict[str, Any]]):
        if len(chips) < max_n and all(c["label"] != label for c in chips):
            chip = {"label": label, "question": question}
            if patch:
                chip["spec_patch"] = patch
            chips.append(chip)

    if subject is None:  # composite template: a related metric + the drafting chip
        if spec.metric == "capex_vs_reserves":
            add("Capex by year", "Show capex by asset year by year",
                {"metric": "capex_actual_cr", "dimensions": ["asset", "fy"]})
        elif spec.metric == "headcount_change":
            add("Current headcount by work centre", "Show current headcount by work centre",
                {"metric": "headcount", "dimensions": ["wc"]})
        elif spec.metric == "pnl_statement":
            fy_cur = (spec.period.fy if spec.period and spec.period.fy else "FY26")
            is_multi = bool((spec.period and spec.period.from_ and spec.period.to and spec.period.from_ != spec.period.to) or ("fy" in spec.dimensions))
            if not is_multi:
                add(f"Show {fy_cur} Balance Sheet (Table)", f"Show ONGC Balance Sheet for {fy_cur}",
                    {"metric": "balance_sheet", "period": {"fy": fy_cur}, "dimensions": [], "chart_kind": "table"})
                add(f"Show {fy_cur} Cash Flow Statement (Table)", f"Show ONGC Cash Flow Statement for {fy_cur}",
                    {"metric": "cash_flow_statement", "period": {"fy": fy_cur}, "dimensions": [], "chart_kind": "table"})
                add(f"Plot {fy_cur} Revenue & Costs Waterfall", f"Plot {fy_cur} revenue and costs as a waterfall chart",
                    {"chart_kind": "waterfall"})
                add("10-year P&L trend (FY17–FY26)", "Show ONGC P&L statement trend from FY17 to FY26",
                    {"metric": "pnl_statement", "period": {"from": "FY17", "to": "FY26"}, "dimensions": ["fy"]})
            else:
                add("Complete FY26 P&L statement", "Show complete Schedule III P&L statement of ONGC for FY26",
                    {"metric": "pnl_statement", "period": {"fy": "FY26"}, "dimensions": []})
                add("Statutory levies (10 yrs)", "Compare Royalty, OIDB Cess and SAED windfall tax from FY17 to FY26",
                    {"metric": "statutory_levies_cr", "period": {"from": "FY17", "to": "FY26"}, "dimensions": ["fy"]})
                add("Group subsidiaries (HPCL, MRPL, OVL)", "Show ONGC subsidiary financials for FY26",
                    {"metric": "subsidiary_pat_cr", "period": {"fy": "FY26"}, "dimensions": ["subsidiary"]})
        elif spec.metric == "balance_sheet":
            fy_cur = (spec.period.fy if spec.period and spec.period.fy else "FY26")
            is_multi = bool((spec.period and spec.period.from_ and spec.period.to and spec.period.from_ != spec.period.to) or ("fy" in spec.dimensions))
            if not is_multi:
                add("10-year Balance Sheet trend (FY17–FY26)", "Show ONGC Balance Sheet trend from FY17 to FY26",
                    {"metric": "balance_sheet", "period": {"from": "FY17", "to": "FY26"}, "dimensions": ["fy"]})
                add(f"Show {fy_cur} Cash Flow Statement", f"Show ONGC Cash Flow Statement for {fy_cur}",
                    {"metric": "cash_flow_statement", "period": {"fy": fy_cur}, "dimensions": []})
                add(f"Show {fy_cur} Financial Ratios", f"Show ONGC Financial Ratios Scorecard for {fy_cur}",
                    {"metric": "financial_ratios", "period": {"fy": fy_cur}, "dimensions": []})
            else:
                add("Complete FY26 Balance Sheet", "Show complete Schedule III Balance Sheet of ONGC for FY26",
                    {"metric": "balance_sheet", "period": {"fy": "FY26"}, "dimensions": []})
                add("Debt vs Cash (10 yrs)", "Compare Total Borrowings and Cash & Bank from FY17 to FY26",
                    {"metric": "total_debt_cr", "period": {"from": "FY17", "to": "FY26"}, "dimensions": ["fy"]})
        elif spec.metric == "cash_flow_statement":
            fy_cur = (spec.period.fy if spec.period and spec.period.fy else "FY26")
            is_multi = bool((spec.period and spec.period.from_ and spec.period.to and spec.period.from_ != spec.period.to) or ("fy" in spec.dimensions))
            if not is_multi:
                add(f"Show {fy_cur} Cash Flow Waterfall", f"Show {fy_cur} Cash Flow statement as a waterfall chart",
                    {"chart_kind": "waterfall"})
                add("10-year Cash Flow trend (FY17–FY26)", "Show ONGC Cash Flow trend from FY17 to FY26",
                    {"metric": "cash_flow_statement", "period": {"from": "FY17", "to": "FY26"}, "dimensions": ["fy"]})
                add(f"Show {fy_cur} Balance Sheet", f"Show ONGC Balance Sheet for {fy_cur}",
                    {"metric": "balance_sheet", "period": {"fy": fy_cur}, "dimensions": []})
            else:
                add("Complete FY26 Cash Flow Statement", "Show complete Ind-AS 7 Cash Flow Statement of ONGC for FY26",
                    {"metric": "cash_flow_statement", "period": {"fy": "FY26"}, "dimensions": []})
        elif spec.metric == "financial_ratios":
            fy_cur = (spec.period.fy if spec.period and spec.period.fy else "FY26")
            add("10-year Ratios trend (FY17–FY26)", "Show ONGC Financial Ratios trend from FY17 to FY26",
                {"metric": "financial_ratios", "period": {"from": "FY17", "to": "FY26"}, "dimensions": ["fy"]})
            add(f"Show {fy_cur} P&L Statement", f"Show ONGC P&L statement for {fy_cur}",
                {"metric": "pnl_statement", "period": {"fy": fy_cur}, "dimensions": []})
            add(f"Show {fy_cur} Balance Sheet", f"Show ONGC Balance Sheet for {fy_cur}",
                {"metric": "balance_sheet", "period": {"fy": fy_cur}, "dimensions": []})
        add("Draft a board note", "Draft a board note on this", None)
        return chips[:4]

    if subject.name == "corporate":
        fy_cur = (spec.period.fy if spec.period and spec.period.fy else "FY26")
        add(f"Complete {fy_cur} P&L Statement", f"Show complete P&L statement of ONGC for {fy_cur}",
            {"metric": "pnl_statement", "period": {"fy": fy_cur}, "dimensions": []})
        add(f"Complete {fy_cur} Balance Sheet", f"Show complete Balance Sheet of ONGC for {fy_cur}",
            {"metric": "balance_sheet", "period": {"fy": fy_cur}, "dimensions": []})
        if "fy" not in spec.dimensions:
            add("10-year trend (FY17–FY26)", "Show the 10-year trend from FY17 to FY26",
                {"period": {"from": "FY17", "to": "FY26"}, "dimensions": ["fy"]})
        add("Draft a briefing note", "Draft a briefing note on this", None)
        return chips[:max_n]

    junior = persona_class(persona) == "junior"
    # 1. Names (roster) — only where named data is allowed.
    if subject.name == "workforce" and grain != "row" and not junior and not spec.is_compare():
        add("Show the names", "Give me their names", {"grain": "row"})
    # 2. Breakdowns not yet applied.
    for d in ("discipline", "grade", "wc", "asset", "field"):
        if d in subject.fields and d not in spec.dimensions and not (
                spec.filter_on(d) and spec.filter_on(d).op == "=" and d in ("wc", "asset", "field")):
            if grain == "row" and subject.name == "workforce":
                patch = {"grain": "aggregate", "dimensions": [d]}
            else:
                patch = {"dimensions": [d]}
            add(_DIM_LABEL[d], f"Break it down by {d.replace('wc', 'work centre')}", patch)
            break
    # 3. Compare a single work centre with a peer.
    for d in ("wc", "asset"):
        f = spec.filter_on(d)
        if f is not None and f.op == "=" and d in subject.fields:
            peer = _peer_wc(str(f.value))
            if peer:
                add(f"Compare with {ents.wc_name(peer)}", f"Compare with {ents.wc_name(peer)}",
                    {"compare": {"field": d, "values": [f.value, peer]}})
            break
    # 4. Trend / time shift where the subject has fiscal years.
    if "fy" in subject.fields and "fy" not in spec.dimensions and not subject.row_only:
        lo = f"FY{int(last_complete_fy()[2:]) - 4:02d}"
        add("5-year trend", "Show the trend over the last 5 years",
            {"period": {"from": lo, "to": last_complete_fy()}, "dimensions": ["fy"]})
    elif subject.row_only and "fy" in subject.fields:
        cur = (spec.period.fy if spec.period and spec.period.fy else subject.default_fy) or last_complete_fy()
        prev = f"FY{int(cur[2:]) - 1:02d}"
        add(f"Same view for {prev}", f"Show the same for {prev}", {"period": {"fy": prev}})
        lo = f"FY{int(last_complete_fy()[2:]) - 4:02d}"
        add("5-year trend", "Show the trend over the last 5 years",
            {"period": {"from": lo, "to": last_complete_fy()}, "dimensions": ["fy"]})
    elif "fy" in subject.fields and "fy" in spec.dimensions and not subject.row_only:
        add(f"Latest year ({last_complete_fy()})", f"Show {last_complete_fy()} only",
            {"period": {"fy": last_complete_fy()}})
    elif subject.name == "workforce" and spec.filter_on("station_tenure_years") and not (spec.period and spec.period.fy):
        add("Same view last year", "What about last year?", {"period": {"fy": last_complete_fy()}})
    # 5. Draft.
    if subject.name == "workforce" and grain == "row" and not junior:
        add("Draft transfer note", "Draft a transfer note for them", None)
    else:
        add("Draft a briefing note", "Draft a briefing note on this", None)
    return chips[:max_n]
