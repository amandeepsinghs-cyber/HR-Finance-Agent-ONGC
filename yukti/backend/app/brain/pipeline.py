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
    dims = [alias.replace("_", " ") for _, alias in compiled.dims]
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
    if plan.intent != "data" or plan.spec is None:
        logger.info(f"planner -> legacy ({plan.intent}; {plan.notes})")
        return None

    spec = plan.spec
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
        logger.warning(f"planner execution failed, legacy fallback: {e}")
        return None
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
    visual = build_visual(spec, compiled, columns, rows, plan.chart_kind, title, subtitle, mode, n_total)
    headline = narrate(spec, compiled, columns, rows, n_total)
    # B4: deterministic insights (+ previous-FY comparison where the subject has fiscal years),
    # drill-down chips, and a narrator limited to computed facts with a numeric-grounding check.
    prev_rows = await _previous_period_rows(spec, compiled, compiler)
    insights = compute_insights(build_insight_context(spec, compiled, rows, n_total, prev_rows,
                                                      scope_phrases(spec, compiled)))
    allowed = allowed_numbers(rows, insights, spec, extra=derived_numbers(compiled, rows, n_total))
    told = compose_spoken(headline, insights, allowed)
    spoken = told["text"]
    if told["ungrounded"]:
        status.append(f"Narrator: ungrounded numbers removed {told['ungrounded']}")
    notes = list(compiled.notes) + [f"Not applied: {d}" for d in compiled.dropped]

    contract: Dict[str, Any] = {
        "turn_id": turn_id,
        "language": language,
        "persona": persona,
        "spoken_summary": spoken,
        "display_text": spoken[:590],
        "visual": visual,
        "insights": [i.text for i in insights][:4] or [s for s in headline.split(". ") if s and "on screen" not in s][:3],
        "insights_v2": [i.to_contract() for i in insights][:6],
        "drilldowns": make_drilldowns(spec, persona, compiled.grain),
        "sources": [{"kind": "data", "object": ", ".join(compiled.tables), "sql": compiled.sql}],
        "suggestions": [],
        "access": {"status": "allowed"},
        "export_options": ["sheets", "xlsx", "pdf"],
        "status_events": status,
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        "generated_sql": compiled.sql,
        "tool_called": "query_data",
        "contract_version": 2,
        "query_spec": spec.to_contract(),
        "context_chips": context_chips(spec, compiled, persona),
    }
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
        last["table"] = {"columns": cols, "rows": rows[:200]}
    else:
        last["type"] = "chart"
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
