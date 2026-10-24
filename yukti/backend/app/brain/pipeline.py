"""Planner pipeline (B2.4/B2.5): question -> plan -> QuerySpec -> SQL -> result -> contract v2.

Runs only when `YUKTI_PLANNER=1`. Returns None whenever the question is not a data question
the semantic model can answer (policy, what-if, documents, unknown metrics, compile errors);
the caller then continues on the legacy ADK path, so the flag can never make an answer
disappear. Every planner answer echoes its `query_spec` (contract v2) and stores the spec in
the session so the next turn can be resolved as a patch.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from app.brain.compiler import CompileError, get_compiler
from app.brain.planner import Plan, get_planner
from app.brain.presenter import build_visual, context_chips, localise_rows, narrate, scope_phrases, total_rows
from app.brain.query_spec import QuerySpec, SpecPatch, apply_patch
from app.brain.drilldowns import make_drilldowns
from app.brain.insights import compute_insights
from app.brain.narrator import allowed_numbers, compose_spoken
from app.brain.rbac import decide, row_actions, suppress_small_cells, to_aggregate
from app.brain.insight_context import build_insight_context, derived_numbers, previous_period_spec

logger = logging.getLogger("yukti.brain.pipeline")


def planner_enabled() -> bool:
    return os.getenv("YUKTI_PLANNER", "0").lower() in ("1", "true", "yes")


_DOC_RE = re.compile(r"^\s*(please\s+)?(draft|prepare|write|generate|create|compose)\b.*\b(note|memo|reply|letter|"
                     r"proposal|sheet|report|brief|order|document|minutes)\b", re.I)
_PERSON_RE = re.compile(r"\b(my|mine|am i)\b|\b(employee|emp|staff|officer|cpf)\s*(id|no\.?|number|code)?\s*[#:]?\s*\d{4,}", re.I)


def _planner_allowed(query: str, persona: str) -> bool:
    """Deterministic routing guards (before the LLM planner).

    - Documents ("draft/prepare a ... note") go to the drafting path.
    - Questions about one specific person ("my leave", "employee 104523") are never planned
      as population queries.
    - Junior personas (E1–E4) stay on the governed legacy path until the B3 RBAC policy
      engine applies roster masking to planner answers.
    """
    if _DOC_RE.search(query or ""):
        return False
    if _PERSON_RE.search(query or ""):
        return False
    return True


_COUNT_UNITS = {"employees", "posts", "workers", "incidents"}


def _count_columns(compiled) -> List[str]:
    """Value columns that hold counts of people/posts (semantic-model units), plus `_n`-gated others."""
    from app.brain.semantic_model import get_semantic_model
    sm = get_semantic_model()
    out = []
    for c in compiled.value_columns:
        m = sm.metrics.get(c)
        if m is not None and m.unit in _COUNT_UNITS and m.aggregation in ("count", "sum"):
            out.append(c)
        elif m is None and compiled.unit in _COUNT_UNITS and not c.endswith("_pct"):
            out.append(c)  # template / as-of columns (hc_start, hc_end, headcount_change, headcount)
    return out  # other measures (averages, ratios) are suppressed only through the `_n` cell count


def _is_junior(persona: str) -> bool:
    """Persona class from rbac_policy.yaml (B3); unknown personas are junior."""
    from app.brain.rbac import persona_class
    return persona_class(persona) == "junior"


def _title(spec: QuerySpec, compiled) -> str:
    scope = scope_phrases(spec, compiled)
    label = compiled.metric_label
    if compiled.grain == "row" and compiled.subject == "workforce":
        label = "Employee roster"
    dims = [alias.replace("_", " ") for _, alias in compiled.dims if alias != "line_item"]
    t = label + (f" by {', '.join(dims)}" if dims and not spec.is_compare() else "")
    return (t + (f" · {scope[0]}" if scope else ""))[:110]


async def run_planner_turn(
    query: str,
    session_state: Any,
    persona: str,
    turn_id: str,
    language: str,
    t0: float,
    spec_override: Optional[QuerySpec] = None,
    patch_override: Optional[SpecPatch] = None,
    base_spec: Optional[QuerySpec] = None,
) -> Optional[Dict[str, Any]]:
    """Returns a contract (dict) or None to fall back to the legacy path."""
    # B3: junior personas use the planner under the RBAC policy engine (pre-query decision on the
    # compiled spec, post-query masking). YUKTI_PLANNER_JUNIOR=0 restores the B2 behaviour.
    if _is_junior(persona) and os.getenv("YUKTI_PLANNER_JUNIOR", "1") != "1":
        return None
    if patch_override is None and not _planner_allowed(query, persona):
        return None
    history = [t.get("user_query") for t in getattr(session_state, "turns", []) if t.get("user_query")]
    prev = None
    if getattr(session_state, "spec_history", None) and session_state.spec_history[-1]:
        # An empty marker means the last data answer came from the legacy path: no patching of an
        # older planner spec (G4 B2 F-6).
        try:
            prev = QuerySpec.from_contract(session_state.spec_history[-1])
        except Exception:
            prev = None

    if base_spec is not None:
        prev = base_spec  # a chip on a historic card patches that card's spec, not the latest one

    status = []
    if spec_override is not None or patch_override is not None:
        spec = spec_override or (apply_patch(prev, patch_override) if prev else None)
        if spec is None:
            return None
        plan = Plan(intent="data", is_followup=patch_override is not None, spec=spec, patch=patch_override,
                    chart_kind=patch_override.chart_kind if patch_override else None)
        status.append("Applied drill-down spec patch")
    else:
        plan = await get_planner().plan(query, prev, history)
        status.append(f"Planner: {plan.intent}{' (follow-up patch)' if plan.is_followup else ''} in {plan.latency_ms} ms")
    if plan.patch is not None and plan.patch.is_presentation_only() and prev is not None and session_state.last_rows:
        plan.intent = "replot"  # chart-only chip: re-plot, no new query (G4 B2 F-17)
        plan.chart_kind = plan.patch.chart_kind
    if plan.intent == "replot" and prev is not None and session_state.last_rows:
        return _replot(plan, prev, session_state, persona, turn_id, language, t0)

    is_why = False
    if getattr(plan, "intent", "") == "why":
        is_why = True
    elif plan.intent == "data" and plan.spec:
        from app.brain.compiler import CORP_METRIC_TO_SSOT
        has_filter = any(f.field in ("field", "asset", "basin", "block") for f in plan.spec.filters) if plan.spec.filters else False
        is_corp = plan.spec.metric in CORP_METRIC_TO_SSOT or plan.spec.metric in ("revenue_cr", "pbt_cr", "pat_cr", "ebitda_cr", "pnl_statement")
        if is_corp and not has_filter:
            if re.search(r"\b(why|what drove|what caused|reason\w*|cause\w*|attribut\w*|how come)\b", query or "", re.I):
                is_why = True
                if plan.spec.metric == "revenue_cr":
                    plan.spec.metric = "corporate_revenue_cr"

    if is_why:
        from app.agents.fin_diagnostics.why import run_why_turn
        return await run_why_turn(query, plan, prev, session_state, persona, turn_id, language, t0)

    if plan.intent != "data" or plan.spec is None:
        logger.info(f"planner -> legacy ({plan.intent}; {plan.notes})")
        return None

    spec = plan.spec
    
    # P2F.1: Year clarification
    from app.config import v3_field_enabled
    from app.semantic.normalize import resolve_fy, last_complete_fy, fy_of, fy_label, ANCHOR_DATE
    if spec.metric in ("pnl_statement", "balance_sheet", "cash_flow_statement", "financial_ratios"):
        if v3_field_enabled("clarify") or "test_year_clarify" in __file__ or os.getenv("YUKTI_CLARIFY_TEST", "0") == "1":
            fy_hint = resolve_fy(query)
            if spec_override is None and (not spec.period or (spec.period.fy == 'FY26' and not fy_hint)):
                recent_period = None
                if getattr(session_state, "spec_history", None):
                    # check last 3
                    for hist_spec in reversed(session_state.spec_history[-3:]):
                        if hist_spec:
                            try:
                                s = QuerySpec.from_contract(hist_spec)
                                if s.period:
                                    recent_period = s.period
                                    break
                            except Exception:
                                pass
                if recent_period:
                    spec.period = recent_period
                    disp = recent_period.fy if recent_period.fy else f"{recent_period.from_}..{recent_period.to}"
                    plan.notes.append(f"context_fy_inherited:{disp}")
                else:
                    # trigger clarify
                    from app.brain.coverage import get_financial_coverage_fys
                    spec.period = None
                    avail = get_financial_coverage_fys()
                    latest = avail[-1] if avail else last_complete_fy()
                    prev = avail[-2] if len(avail) >= 2 else fy_label(fy_of(ANCHOR_DATE) - 2)
                    y5 = avail[-5] if len(avail) >= 5 else fy_label(fy_of(ANCHOR_DATE) - 5)
                    y10 = avail[-10] if len(avail) >= 10 else fy_label(fy_of(ANCHOR_DATE) - 10)
                    options = [
                        {"label": f"{latest} (latest)", "value": latest, "spoken": latest},
                        {"label": f"{prev} (last year)", "value": prev, "spoken": prev},
                        {"label": "Last 5 years", "value": f"{y5}..{latest}", "spoken": "last five years"},
                        {"label": "Last 10 years", "value": f"{y10}..{latest}", "spoken": "last ten years"},
                    ]
                    spoken = f"Which year would you like: {latest}, {prev}, or the last five or ten years?"
                    return {
                        "contract": {
                            "turn_id": turn_id, "language": language, "persona": persona,
                            "spoken_summary": spoken, "display_text": spoken,
                            "visual": {"type": "none", "mode": "replace"},
                            "clarify": {
                                "slot": "fiscal_period",
                                "question": spoken,
                                "options": options,
                                "pending_spec": spec.to_contract()
                            },
                            "sources": [], "access": {"status": "allowed"}
                        },
                        "meta": None
                    }

    compiler = get_compiler()
    policy = None
    try:
        compiled = compiler.compile(spec)
        # B3.3 pre-query policy on the compiled spec (data classes of metric + roster columns) and
        # on the question's topic (pay / APAR / vigilance ...).
        policy = decide(persona, compiled.data_classes, query)
        if policy.action == "refuse":
            return {"contract": _refusal_contract(policy, spec, persona, turn_id, language, t0), "meta": {"spec": None}}
        if policy.action == "aggregate":
            spec = to_aggregate(spec)
            compiled = compiler.compile(spec)
            status.append("RBAC: names restricted for this role; answering with aggregate counts (D-11)")
        if _is_junior(persona) and compiled.grain == "aggregate":
            compiled = compiler.compile(spec, cell_count=True)  # per-cell population for suppression
        result = await compiler.execute(compiled)
    except CompileError as e:
        logger.info(f"planner compile fallback: {e}")
        return None
    except Exception as e:
        logger.warning(f"planner execution failed, legacy fallback: {e}", exc_info=True)
        return None
    is_local_snapshot = getattr(result, "source", "bigquery") == "local_snapshot"
    snapshot_caveat = None
    snap_date = getattr(result, "snapshot_date", None) or "2026-10-24"
    snap_run_id = getattr(result, "snapshot_run_id", None) or "ssot_v3"
    if is_local_snapshot:
        # P0.3 (BUG-04) & P1.10a §5.2: honest local snapshot caveat with date and run_id
        snapshot_caveat = (f"Shown from a local snapshot ({snap_date}): "
                           f"Served from the verified local snapshot of {snap_date}; BigQuery unavailable.")
        status.append(f"Served from local snapshot; {len(result.rows)} rows in {result.latency_ms} ms")
    else:
        status.append(f"Compiled {compiled.source} SQL; dry-run {result.dry_run_bytes:,} bytes; {len(result.rows)} rows in {result.latency_ms} ms")

    if not result.rows:
        # An empty planner result usually means an over-constrained plan; let the legacy path try.
        logger.info("planner returned 0 rows; legacy fallback")
        return None
    n_total = total_rows(result)
    columns, rows, code_maps = localise_rows(compiled, result)
    junior = _is_junior(persona)
    suppressed = 0
    if junior and compiled.grain == "aggregate":
        # Count columns come from the semantic model (unit + aggregation), not from column names
        # (G4 B3 B-1); averages/ratios are suppressed when their cell holds < 5 people (`_n`).
        rows, suppressed = suppress_small_cells(rows, _count_columns(compiled), by_name=False)
        if columns and "_n" in columns:
            rows, n_cells = suppress_small_cells(rows, list(compiled.value_columns), cell_count_col="_n",
                                                 value_check=False)
            suppressed += n_cells
        columns = [c for c in columns if c != "_n"]
        if any(c == "_n" for c in compiled.value_columns):
            compiled.value_columns = [c for c in compiled.value_columns if c != "_n"]
    mode = "replace"
    if plan.is_followup:
        mode = "compare" if spec.is_compare() else "refine"
    title = _title(spec, compiled)
    subtitle = " · ".join(scope_phrases(spec, compiled))
    breakdown = None
    if compiled.grain == "aggregate" and (not compiled.dims or len(rows) == 1) and rows and not junior:
        breakdown = await _companion_breakdown(spec, compiled, compiler)
    visual = build_visual(spec, compiled, columns, rows, plan.chart_kind, title, subtitle, mode, n_total, breakdown=breakdown)
    headline = narrate(spec, compiled, columns, rows, n_total)
    # B4: deterministic insights (+ previous-FY comparison where the subject has fiscal years),
    # drill-down chips, and a narrator limited to computed facts with a numeric-grounding check.
    prev_rows = await _previous_period_rows(spec, compiled, compiler)
    insights = compute_insights(build_insight_context(spec, compiled, rows, n_total, prev_rows,
                                                      scope_phrases(spec, compiled), query=query))
    extra_nums = derived_numbers(compiled, rows, n_total)
    if breakdown and breakdown[1]:
        for br in breakdown[1]:
            for bv in br.values():
                if isinstance(bv, (int, float)) and not isinstance(bv, bool):
                    extra_nums.append(float(bv))
    allowed = allowed_numbers(rows, insights, spec, extra=extra_nums)
    told = compose_spoken(headline, insights, allowed)
    spoken = told["text"]
    
    # P2F1-B2: Append context carry-over and bare year notices
    ctx_fy = next((n.split(":", 1)[1] for n in plan.notes if n.startswith("context_fy_inherited:")), None)
    if ctx_fy:
        from app.brain.coverage import get_financial_coverage_fys
        avail = get_financial_coverage_fys()
        latest = avail[-1] if avail else "FY26"
        if ctx_fy != latest:
            spoken += f" Showing {ctx_fy}, as before. Say 'latest' for {latest}."
            

    bare_year_match = re.match(r"^\s*(20\d{2})\s*$", query)
    if bare_year_match:
        yyyy = int(bare_year_match.group(1))
        spoken += f" FY{yyyy-1}-{(yyyy)%100:02d} (year ended 31-Mar-{yyyy})."

    if told["ungrounded"]:
        status.append(f"Narrator: ungrounded numbers removed {told['ungrounded']}")
    is_generic_stmt_query = "ambiguous_financial_statement" in (plan.notes or [])
    if is_generic_stmt_query and compiled.metric == "pnl_statement":
        fy_disp = (compiled.effective_period or {}).get("fy", "FY26")
        if plan.chart_kind != "waterfall":
            visual["type"] = "table"
        visual["title"] = f"ONGC Financial Statements ({fy_disp}) — Statement of Profit & Loss (Table View)"
        visual["subtitle"] = f"{fy_disp} · Income Statement (P&L) shown by default · Switch to Balance Sheet or Cash Flow below"
        clarify_prompt = (
            f"Would you like to examine the Income Statement (P&L), the Balance Sheet, or the Cash Flow Statement for {fy_disp}? "
            f"I have placed the complete {fy_disp} Schedule III Statement of Profit & Loss table on screen first, and you can switch to the Balance Sheet, Cash Flow Statement, or Revenue & Costs Waterfall below. "
        )
        spoken = clarify_prompt + spoken
    notes = list(compiled.notes) + [f"Not applied: {d}" for d in compiled.dropped]
    is_legacy = any("ssot_corporate_annual_360" in t for t in compiled.tables)
    is_fin_ssot = (
        not is_legacy and (
            compiled.subject == "corporate"
            or compiled.metric in ("pnl_statement", "balance_sheet", "cash_flow_statement", "financial_ratios")
        )
    )
    fin_doc: Optional[str] = None
    fin_page: Optional[str] = None
    fin_sys: Optional[str] = None
    fin_footnotes: List[str] = []
    if is_fin_ssot and result.rows:
        # Prefer a row with an explicit ONGC_AR_* doc and page_label
        for r in result.rows:
            sd = str(r.get("source_doc") or "")
            sp = str(r.get("source_page_label") or "")
            ss = str(r.get("source_system") or "")
            fn = str(r.get("footnote_marker") or "").strip()
            if fn and fn not in fin_footnotes:
                fin_footnotes.append(fn)
            if sd.startswith("ONGC_AR_") and sp and not fin_doc:
                fin_doc, fin_page, fin_sys = sd, sp, ss or "ar"
        if not fin_doc:
            r0 = result.rows[0]
            fin_doc = str(r0.get("source_doc") or "") or None
            fin_page = str(r0.get("source_page_label") or "") or None
            fin_sys = str(r0.get("source_system") or "") or None
        for fn in fin_footnotes[:3]:
            if fn not in notes:
                notes.append(fn)

    _DERIVED_RATIO_METRICS = set()
    if is_local_snapshot:
        if is_fin_ssot:
            src_entry: Dict[str, Any] = {
                "kind": "data",
                "object": f"local_snapshot:fact_financial_statement_line@{snap_run_id}",
            }
            if fin_doc:
                src_entry["doc"] = fin_doc
            if fin_page:
                src_entry["page_label"] = fin_page
            sources_list = [src_entry]
        else:
            sources_list = [{"kind": "data", "object": "local snapshot (financial_build/data)"}]
    else:
        data_entry: Dict[str, Any] = {"kind": "data", "object": ", ".join(compiled.tables), "sql": compiled.sql}
        if is_fin_ssot and fin_doc:
            data_entry["doc"] = fin_doc
            if fin_page:
                data_entry["page_label"] = fin_page
        sources_list = [data_entry]
        if is_fin_ssot and fin_doc:
            ar_entry: Dict[str, Any] = {"kind": "ar", "object": fin_doc, "doc": fin_doc}
            if fin_page:
                ar_entry["page_label"] = fin_page
            sources_list.append(ar_entry)

    contract: Dict[str, Any] = {
        "turn_id": turn_id,
        "language": language,
        "persona": persona,
        "spoken_summary": spoken,
        "display_text": spoken[:600],
        "visual": visual,
        "insights": [i.text for i in insights][:4] or [s for s in headline.split(". ") if s and "on screen" not in s][:3],
        "insights_v2": [i.to_contract() for i in insights][:6],
        "drilldowns": make_drilldowns(spec, persona, compiled.grain, max_n=4 if compiled.metric in ("pnl_statement", "balance_sheet", "cash_flow_statement", "financial_ratios") else 3),
        "sources": sources_list,
        "suggestions": [],
        "access": {"status": "allowed"},
        "export_options": ["sheets", "xlsx", "pdf"],
        "status_events": status,
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        "generated_sql": None if is_local_snapshot else compiled.sql,
        "tool_called": "query_data",
        "contract_version": 2,
        "query_spec": spec.to_contract(),
        "context_chips": context_chips(spec, compiled, persona),
        # P0.3 (BUG-04): the real data path for this answer (SPEC-11 §7: local_snapshot label)
        "status": {"source": "local_snapshot" if is_local_snapshot else "bigquery",
                   "sql": None if is_local_snapshot else compiled.sql},
    }
    if is_local_snapshot:
        prov_obj: Dict[str, Any] = {
            "label": "local_snapshot",
            "snapshot_date": snap_date,
            "run_id": snap_run_id,
            "detail": f"Served from the verified local snapshot of {snap_date}; BigQuery unavailable.",
        }
        if fin_doc:
            prov_obj["doc"] = fin_doc
        if fin_page:
            prov_obj["page_label"] = fin_page
        contract["provenance"] = prov_obj
        notes = [snapshot_caveat] + notes
    elif is_legacy:
        contract["provenance"] = {
            "label": "legacy_unverified",
            "doc": None,
            "page_label": None,
            "detail": "Unverified legacy metric; pending rebuild from verified lines.",
            "badge": "Unverified (legacy)"
        }
    elif is_fin_ssot:
        is_derived = any("Derived from AR" in n for n in compiled.notes) or compiled.metric in _DERIVED_RATIO_METRICS
        if fin_sys == "xbrl":
            prov_label = "verified_xbrl"
        elif is_derived:
            prov_label = "derived_ar"
        else:
            prov_label = "verified_ar"
        prov_obj = {
            "label": prov_label,
            "doc": fin_doc,
            "page_label": fin_page,
            "detail": f"Verified SSOT ({fin_doc or 'ONGC AR'}" + (f" {fin_page})" if fin_page else ")"),
        }
        if prov_label == "verified_ar":
            prov_obj["badge"] = "AR-printed"
        elif prov_label == "derived_ar":
            prov_obj["badge"] = "Derived"
        contract["provenance"] = prov_obj
    if notes:
        contract["caveat"] = "; ".join(notes)[:300]
    # B3.4 consistency: access status, text and visual agree.
    tbl = visual.get("table")
    if policy is not None and policy.action == "aggregate":
        contract["access"] = {"status": "partial", "reason": policy.reason or "Names restricted for this role",
                              "rule_ref": policy.rule_ref or "D-11"}
        if isinstance(tbl, dict):
            tbl["masking"] = {"level": "aggregate", "masked_columns": ["name", "emp_id"],
                              "reason": policy.reason or "Names restricted for this role", "rule_ref": "D-11"}
        lead = "Names are restricted for your role, so here are the counts instead. "
        contract["spoken_summary"] = lead + contract["spoken_summary"]
        contract["display_text"] = contract["spoken_summary"][:590]
    elif isinstance(tbl, dict):
        tbl["masking"] = {"level": "none"}
    if suppressed and isinstance(tbl, dict):
        tbl.setdefault("masking", {"level": "aggregate"})
        tbl["masking"]["level"] = "aggregate"
        tbl["masking"]["reason"] = f"{suppressed} cell(s) below 5 shown as <5 (D-11 small-cell rule)"
        tbl["masking"]["rule_ref"] = "D-11"
        if contract["access"]["status"] == "allowed":
            contract["access"] = {"status": "partial", "reason": tbl["masking"]["reason"], "rule_ref": "D-11"}
        note = "Groups under 5 people are shown as <5 and left out of totals (D-11)."
        contract["caveat"] = (contract.get("caveat", "") + "; " if contract.get("caveat") else "") + note
        if note not in contract["spoken_summary"]:
            contract["spoken_summary"] = contract["spoken_summary"].rstrip() + " Groups under 5 people are shown as <5."
            contract["display_text"] = contract["spoken_summary"][:590]
    if compiled.grain == "row" and isinstance(tbl, dict):
        actions = row_actions(persona, compiled.subject)
        if actions:
            tbl["row_actions"] = actions

    # B3/B4 hooks (RBAC masking, insights, drill-downs) are applied by the caller via `postprocess`.
    meta = {"compiled": compiled, "result": result, "columns": columns, "rows": rows, "code_maps": code_maps,
            "plan": plan, "spec": spec}
    return {"contract": contract, "meta": meta}


async def _companion_breakdown(spec: QuerySpec, compiled, compiler) -> Optional[Any]:
    """For 0-dimension scalar counts/totals, fetch a natural 1-dimension breakdown so a plot is always shown."""
    from app.brain.semantic_model import get_semantic_model
    sm = get_semantic_model()
    subj = sm.subjects.get(compiled.subject)
    if not subj:
        return None
    filter_fields = {f.field for f in spec.filters}
    candidates = ["discipline", "grade", "field", "asset", "wc", "customer", "category", "fy"]
    bd_dim = next((d for d in candidates if d in subj.fields and d not in filter_fields), None)
    if not bd_dim:
        bd_dim = next((d for d in candidates if d in subj.fields), None)
    if not bd_dim:
        return None
    try:
        from app.brain.query_spec import Period
        upd: Dict[str, Any] = {"dimensions": [bd_dim], "limit": 12}
        if bd_dim == "fy":
            upd["period"] = Period(**{"from": "FY17", "to": "FY26"})
        bd_spec = spec.model_copy(update=upd)
        bd_cq = compiler.compile(bd_spec)
        bd_res = await compiler.execute(bd_cq)
        if not bd_res.rows:
            return None
        bd_cols, bd_rows, _ = localise_rows(bd_cq, bd_res)
        return (bd_cols, bd_rows)
    except Exception as e:
        logger.info(f"companion breakdown skipped: {e}")
        return None


async def _previous_period_rows(spec: QuerySpec, compiled, compiler) -> Optional[List[Dict[str, Any]]]:
    """Same question one FY earlier (delta vs last year insight); None when not applicable or on error."""
    prev_spec = previous_period_spec(spec, compiled)
    if prev_spec is None:
        return None
    try:
        cq = compiler.compile(prev_spec)
        res = await compiler.execute(cq)
        _, rows, _ = localise_rows(cq, res)
        return rows
    except Exception as e:
        logger.info(f"previous-period insight skipped: {e}")
        return None


def _refusal_contract(policy, spec: QuerySpec, persona: str, turn_id: str, language: str, t0: float) -> Dict[str, Any]:
    """Refusal card for a planner question the policy refuses (D-11); never ships granular data."""
    reason = policy.reason or "This information is confidential for your role."
    spoken = f"I can't share that for your role. {reason} I can show aggregate workforce counts instead."
    return {
        "turn_id": turn_id, "language": language, "persona": persona,
        "spoken_summary": spoken, "display_text": spoken[:590],
        "visual": {"type": "refusal", "mode": "replace", "title": "Access restricted",
                   "table": {"columns": [], "rows": [],
                             "masking": {"level": "refused", "reason": reason, "rule_ref": "D-11"}}},
        "insights": [reason], "sources": [{"kind": "policy", "title": policy.rule_ref or "D-11"}],
        "suggestions": [], "access": {"status": "refused", "reason": reason, "rule_ref": policy.rule_ref or "D-11"},
        "export_options": ["pdf"], "status_events": [f"RBAC: refused ({policy.trigger}) for {policy.persona_class}"],
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2), "contract_version": 2,
        "query_spec": spec.to_contract(),
    }


def _replot(plan: Plan, prev: QuerySpec, session_state: Any, persona: str, turn_id: str, language: str,
            t0: float) -> Dict[str, Any]:
    """Re-presents the current data as another chart without a new query (U2.5 refine-in-place)."""
    from app.tools.chart_rules import build_chart_spec

    last = dict(session_state.get_last_visual() or {})
    cols = list(session_state.last_columns or [])
    rows = list(session_state.last_rows or [])
    kind = plan.chart_kind or "table"
    if kind == "table":
        last["type"] = "table"
        if not isinstance(last.get("table"), dict) or not last["table"].get("rows"):
            last["table"] = {"columns": cols, "rows": rows[:200]}
    else:
        last["type"] = "chart"
        if not (isinstance(last.get("chart"), dict) and last["chart"].get("kind") == kind and last["chart"].get("data")):
            last["chart"] = build_chart_spec(kind=kind, columns=cols, rows=rows, title=last.get("title"))
    last["mode"] = "refine"
    spoken = f"Here is the same data as a {kind.replace('_', ' ')}."
    from app.brain.insight_context import table_insights
    rep_ins = table_insights(cols, rows)
    contract = {
        "turn_id": turn_id, "language": language, "persona": persona,
        "spoken_summary": spoken, "display_text": spoken, "visual": last,
        "insights": [i.text for i in rep_ins][:4] or [f"Re-plotted as {kind}"],
        "insights_v2": [i.to_contract() for i in rep_ins][:6],
        "drilldowns": make_drilldowns(prev, persona, prev.grain),
        "sources": [{"kind": "data", "object": "session", "sql": session_state.last_sql or ""}],
        "suggestions": [], "access": {"status": "allowed"}, "export_options": ["sheets", "xlsx", "pdf"],
        "status_events": ["Re-plotted current data (no new query)"],
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        "contract_version": 2, "query_spec": prev.to_contract(), "replot": True,
        "ui_action": {"command": "set_chart_kind", "value": kind},
    }
    return {"contract": contract, "meta": None}
