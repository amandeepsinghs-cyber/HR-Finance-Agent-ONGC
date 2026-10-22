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


# Junior personas (D-11, OD-5 option a). B2 keeps them on the governed legacy path; B3's policy
# engine (app/brain/rbac.py) replaces this set with the rbac_policy.yaml persona classes.
_SENIOR_PERSONAS = {"CMD", "DIR_HR", "DIR_FIN"}


def _is_junior(persona: str) -> bool:
    return persona not in _SENIOR_PERSONAS  # unknown personas are treated as junior


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
    # RBAC first, for every input incl. client-sent spec patches (G4 B2 F-1).
    if _is_junior(persona) and os.getenv("YUKTI_PLANNER_JUNIOR", "0") != "1":
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
    try:
        compiled = compiler.compile(spec)
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
    mode = "replace"
    if plan.is_followup:
        mode = "compare" if spec.is_compare() else "refine"
    title = _title(spec, compiled)
    subtitle = " · ".join(scope_phrases(spec, compiled))
    visual = build_visual(spec, compiled, columns, rows, plan.chart_kind, title, subtitle, mode, n_total)
    spoken = narrate(spec, compiled, columns, rows, n_total)
    notes = list(compiled.notes) + [f"Not applied: {d}" for d in compiled.dropped]

    contract: Dict[str, Any] = {
        "turn_id": turn_id,
        "language": language,
        "persona": persona,
        "spoken_summary": spoken,
        "display_text": spoken[:590],
        "visual": visual,
        "insights": [s for s in spoken.split(". ") if s and "on screen" not in s][:3] or [spoken[:200]],
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

    # B3/B4 hooks (RBAC masking, insights, drill-downs) are applied by the caller via `postprocess`.
    meta = {"compiled": compiled, "result": result, "columns": columns, "rows": rows, "code_maps": code_maps,
            "plan": plan, "spec": spec}
    return {"contract": contract, "meta": meta}


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
    contract = {
        "turn_id": turn_id, "language": language, "persona": persona,
        "spoken_summary": spoken, "display_text": spoken, "visual": last,
        "insights": [f"Re-plotted as {kind}"],
        "sources": [{"kind": "data", "object": "session", "sql": session_state.last_sql or ""}],
        "suggestions": [], "access": {"status": "allowed"}, "export_options": ["sheets", "xlsx", "pdf"],
        "status_events": ["Re-plotted current data (no new query)"],
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        "contract_version": 2, "query_spec": prev.to_contract(), "replot": True,
        "ui_action": {"command": "set_chart_kind", "value": kind},
    }
    return {"contract": contract, "meta": None}
