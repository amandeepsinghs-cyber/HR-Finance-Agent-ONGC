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
from app.brain.semantic_model import get_semantic_model
from app.access_control import UnknownPersona
import time
import asyncio
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
    return os.getenv("YUKTI_PLANNER", "1").lower() not in ("0", "false", "no")


_DOC_RE = re.compile(r"^\s*(please\s+)?(draft|prepare|write|generate|create|compose|send|export|download)\b.*\b(note|memo|reply|letter|"
                     r"proposal|sheet|report|brief|order|document|minutes|email|file|excel|xlsx|csv|ईमेल|पत्र)\b", re.I)
# SPEC-06 §4.5: _PERSON_RE no longer blocks "my/mine/am i" (those use self_scope -> @self_emp_id).
_PERSON_RE = re.compile(r"\b(employee|emp|staff|officer|cpf)\s*(id|no\.?|number|code)?\s*[#:]?\s*\d{4,}", re.I)


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
    principal: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """Returns a contract (dict) or None to fall back to the legacy path."""
    # B3: junior personas use the planner under the RBAC policy engine (pre-query decision on the
    # compiled spec, post-query masking). YUKTI_PLANNER_JUNIOR=0 restores the B2 behaviour.
    if _is_junior(persona) and os.getenv("YUKTI_PLANNER_JUNIOR", "1") != "1":
        return None
    if patch_override is None and not _planner_allowed(query, persona):
        # 1. Check export intent
        from app.ui_control import detect_ui_control_intent
        ui_intent = detect_ui_control_intent(query)
        is_export = ui_intent and ui_intent.get("action") == "export" and ui_intent.get("value") == "xlsx"
        if not is_export and query and re.search(r"\b(export|excel|xlsx|csv|download)\b", query, re.I):
            ui_intent = {"action": "export", "value": "xlsx", "columns": "Name, Designation, Grade, Continuous Stay"}
            is_export = True

        if is_export:
            from app.tools.export_tool import DocumentExporter
            from app.export_audit import write_export_audit, build_export_filename, _collapse_roster_to_grade_counts, register_artifact
            import uuid
            export_id = f"exp_{uuid.uuid4().hex}"
            
            active_cohort = session_state.get_active_cohort() or {}
            last_turn = session_state.turns[-1] if getattr(session_state, "turns", []) else {}
            last_vis = (last_turn.get("visual") or {}) if isinstance(last_turn, dict) else {}
            tbl = last_vis.get("table") or {}
            
            cols_str = ui_intent.get("columns", "")
            req_cols = [c.strip() for c in cols_str.split(",") if c.strip()] if cols_str else []
            
            HEADER_TO_KEY = {
                "Name": "name",
                "Designation": "functional_designation",
                "Level": "grade",
                "Tenure in Delhi (yrs)": "delhi_tenure_years",
                "ONGC service (yrs)": "ongc_tenure_years",
                "Years to retirement": "years_to_retirement",
                "Exemption": "exemption"
            }
            
            is_aggregate = persona == "DIR_FIN" or persona.startswith("E")
            filename = build_export_filename("delhi_gt5y_roster", "WC-DEL".lower(), "asof-20261019", persona.lower(), "xlsx", is_aggregate=is_aggregate)
            
            caveat_msg = None
            if is_aggregate:
                export_cols = ["grade", "headcount"]
                export_headers = {"grade": "Level", "headcount": "Executives"}
                raw_rows = active_cohort.get("rows") or tbl.get("rows") or []
                if raw_rows and "headcount" in raw_rows[0]:
                    export_rows = raw_rows
                else:
                    _, _, export_rows = _collapse_roster_to_grade_counts(raw_rows, suppress_under_5=persona.startswith("E"))
            else:
                export_rows = active_cohort.get("rows") or tbl.get("rows") or []
                export_cols = []
                export_headers = {}
                unknown = []
                for c in req_cols:
                    if c in HEADER_TO_KEY:
                        k = HEADER_TO_KEY[c]
                        export_cols.append(k)
                        export_headers[k] = c
                    else:
                        unknown.append(c)
                if not export_cols:
                    export_cols = ["name", "functional_designation", "grade", "ongc_tenure_years", "delhi_tenure_years", "years_to_retirement", "exemption"]
                    export_headers = {k: next(c for c, v in HEADER_TO_KEY.items() if v == k) for k in export_cols}
                if unknown:
                    caveat_msg = f"I couldn't match '{unknown[0]}'; exported the rest"
            
            contract_obj = {
                "visual": {
                    "title": "Delhi executives with > 5 years' continuous stay — as of 19-Oct-2026 — source: SSOT (synthetic, Illustrative)",
                    "table": {"columns": export_cols, "headers": export_headers, "rows": export_rows}
                },
                "definition_id": "DELHI_GT5_CONT_V1",
                "query_spec": {"as_of": "2026-10-19"}
            }
            
            exporter = DocumentExporter()
            # write as {export_id}.xlsx for main.py lookup
            from app.config import EXPORTS_DIR
            disk_filename = f"{export_id}.xlsx"
            file_path = exporter.export_xlsx(
                columns=export_cols,
                rows=export_rows,
                filename=disk_filename,
                persona=persona,
                masked=is_aggregate,
                contract=contract_obj
            )
            
            rec = register_artifact(
                export_id=export_id,
                disk_path=EXPORTS_DIR / disk_filename,
                kind="xlsx",
                filename=filename,
                rows=len(export_rows),
                columns=export_cols,
                
                masked=is_aggregate,
                is_aggregate=is_aggregate,
                emp_id=principal.emp_id if principal else "EMP-000000",
                persona=persona,
                session_id=getattr(session_state, "session_id", ""),
                turn_id=turn_id
            )
            
            write_export_audit(
                emp_id=principal.emp_id if principal else "EMP-000000",
                persona=persona,
                session_id=getattr(session_state, "session_id", ""),
                turn_id=turn_id,
                fmt="xlsx",
                filename=filename,
                sha256=rec.sha256,
                rows=len(export_rows),
                columns=export_cols,
                
                masked=is_aggregate,
                delivery="download",
                data_classes=["general"],
        client_ip="test"
            )
            
            art_obj = {
                "export_id": export_id,
                "kind": "xlsx",
                "filename": filename,
                "url": f"/api/export/{export_id}",
                "rows": len(export_rows),
                "columns": export_cols,
                "masked": is_aggregate,
                "sha256": rec.sha256,
                "created_at": rec.created_at,
                "expires_at": rec.expires_at
            }
            if active_cohort:
                if "artifacts" not in active_cohort:
                    active_cohort["artifacts"] = []
                active_cohort["artifacts"].append(art_obj)
            
            display_text = "Here is the Excel export you requested."
            if caveat_msg:
                display_text = caveat_msg + ". " + display_text
            contract = {
                "contract_version": 2,
                "turn_id": turn_id,
                "language": language,
                "display_text": display_text,
                "spoken_summary": "I have prepared the Excel export.",
                "artifacts": [art_obj],
                "ui_action": {"type": "download", "export_id": export_id}
            }
            return {"contract": contract, "meta": None}

        # 2. Check email/letter routing
        if _DOC_RE.search(query or "") and re.search(r"\b(email|letter|ईमेल|पत्र)\b", query, re.I):
            from app.brain.email_agent import build_email_draft
            contract = await asyncio.to_thread(
                build_email_draft,
                query=query,
                session_state=session_state,
                persona=persona,
                turn_id=turn_id,
                language=language
            )
            return {"contract": contract, "meta": None}

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
        await asyncio.sleep(0)
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
        elif not has_filter and re.search(r"\b(why|what drove|what caused)\b.*\b(pat|pbt|profit|revenue|opex|royalty|saed|windfall|levies|dd&a|finance\s+cost|exchange\s+loss|provision|other\s+income)\b", query or "", re.I):
            is_why = True

    if is_why:
        from app.agents.fin_diagnostics.why import run_why_turn
        return await run_why_turn(query, plan, prev, session_state, persona, turn_id, language, t0)

    if re.search(r"\b(top\s*(?:5|five)\s*actions|quantified\s+actions|what\s+actions\s+(?:can|should)\s+we\s+take)\b", query or "", re.I):
        from pathlib import Path
        import pandas as pd
        from app.agents.fin_diagnostics.actions import generate_actions
        from app.semantic.normalize import resolve_fy
        fy_hint = resolve_fy(query)
        fy_act = (fy_hint.get("fy") if isinstance(fy_hint, dict) and fy_hint.get("fy") else None) or "FY26"
        snap_path = Path(os.getenv("YUKTI_FIN_SNAPSHOT_PATH") or (Path(__file__).resolve().parents[4] / "financial_ssot" / "out" / "fact_snapshot.parquet"))
        levers_path = Path(__file__).resolve().parents[1] / "agents" / "fin_diagnostics" / "levers.yaml"
        df_act = pd.read_parquet(snap_path)
        act_payload = generate_actions(df_act, fy_act, persona=persona, levers_path=levers_path)
        items = act_payload.get("items") or []
        top_titles = ", ".join(str(it.get("title") or "") for it in items[:3])
        summary_act = f"Here are the top {len(items)} quantified actions for {fy_act}: {top_titles}." if items else f"Here are the quantified actions for {fy_act}."
        return {
            "contract": {
                "contract_version": 3,
                "turn_id": turn_id,
                "language": language,
                "persona": persona,
                "spoken_summary": summary_act,
                "display_text": summary_act,
                "visual": {
                    "type": "actions",
                    "mode": "replace",
                    "title": f"Top 5 Quantified Actions — {fy_act}",
                    "actions": act_payload,
                },
                "actions": act_payload,
                "insights": [str(it.get("what_to_do") or "") for it in items[:3] if it.get("what_to_do")],
                "sources": [{"kind": "data", "object": "hrfin_gold.fact_financial_statement_line", "title": f"ONGC Standalone SSOT ({fy_act})"}],
                "suggestions": [],
                "access": {"status": "allowed"},
                "export_options": ["pdf", "xlsx"],
                "status_events": [f"Generated {len(items)} quantified actions for {fy_act}"],
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            },
            "meta": None,
        }

    if plan.intent == "what_if":
        # M-B4 / SPEC-11 §2 row 17: what_if runs after RBAC (finance personas only) using grounded numbers from ssot_field_economics_360
        from app.brain.rbac import persona_function
        from app.answer_composer import build_refusal_contract
        from app.tools.what_if import run_what_if_simulation
        from app.tools.chart_rules import build_chart_spec

        if persona_function(persona) not in ("EXEC", "FIN"):
            ref_wi = build_refusal_contract(
                code="R-FUNC",
                persona=persona,
                turn_id=turn_id,
                language=language,
                rule_ref="D-43",
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            )
            return {"contract": ref_wi, "meta": {"spec": None}}

        m_price = re.search(r"\$\s*(\d+(?:\.\d+)?)", query or "")
        brent_val = float(m_price.group(1)) if m_price else 60.0
        sim_res = await asyncio.to_thread(
            run_what_if_simulation,
            scenario=query,
            brent_price=brent_val,
            persona=persona,
        )
        rows = sim_res.get("rows") or []
        columns = sim_res.get("columns") or []
        sql = sim_res.get("sql") or ""
        neg_fields = [str(r.get("field_name")) for r in rows if r.get("is_ebitda_negative") or r.get("is_pbt_negative")]
        price_lbl = int(brent_val) if brent_val == int(brent_val) else brent_val
        if any(k in (query or "").lower() for k in ("brent", "crude", "price")):
            if neg_fields:
                headline_wi = (
                    f"At a simulated Brent crude price of ${price_lbl} per barrel, {len(neg_fields)} fields "
                    f"({', '.join(neg_fields[:3])}) turn negative on PBT or cash margin."
                )
            else:
                headline_wi = f"At a simulated Brent crude price of ${price_lbl} per barrel, field profitability across {len(rows)} assets has been simulated."
            title_wi = f"What-If: Brent ${price_lbl}/bbl Oil Price Shock Sensitivity"
        else:
            headline_wi = f"Simulated scenario across {len(rows)} records."
            title_wi = "What-If Scenario Simulation"
        allowed_wi = allowed_numbers(rows, [], QuerySpec(metric="pbt_cr"), extra=[ float(price_lbl), float(len(neg_fields)), float(len(rows)) ])
        told_wi = compose_spoken(headline_wi, [], allowed_wi, language=language)
        spoken_wi = told_wi["text"]
        chart_spec = build_chart_spec(kind="hbar", columns=columns, rows=rows, title=title_wi) if rows and len(columns) >= 2 else None
        vis_wi: Dict[str, Any] = {
            "type": "chart" if chart_spec else "table",
            "mode": "replace",
            "title": title_wi,
            "table": {"columns": columns, "rows": rows[:25]},
        }
        if chart_spec:
            vis_wi["chart"] = chart_spec
        wi_contract = {
            "turn_id": turn_id,
            "language": language,
            "persona": persona,
            "spoken_summary": spoken_wi,
            "display_text": spoken_wi,
            "visual": vis_wi,
            "insights": [spoken_wi],
            "sources": [{"kind": "data", "object": "hrfin_gold.ssot_field_economics_360", "sql": sql}],
            "suggestions": ["Draft a board note on this", "Show as a table"],
            "access": {"status": "allowed"},
            "export_options": ["pdf", "xlsx"],
            "status_events": ["Executed What-If simulation on hrfin_gold.ssot_field_economics_360"],
            "tool_called": "what_if",
        }
        return {"contract": wi_contract, "meta": None}

    # D-66: APAR and medical records for EMP-000001..3 are refused for EVERY persona (even when plan.intent != 'data')
    from app.brain.rbac import apply_office_holder_safeguard, is_office_holder_apar_or_medical

    oh_ref_code = is_office_holder_apar_or_medical(persona, question=query, spec=plan.spec)
    if oh_ref_code:
        try:
            pol_oh = decide(persona, ["apar"] if oh_ref_code == "R-APAR" else ["sensitive"], query, spec=plan.spec)
        except UnknownPersona:
            pol_oh = decide("E1_HR", ["apar"] if oh_ref_code == "R-APAR" else ["sensitive"], query, spec=plan.spec)
        return {"contract": _refusal_contract(pol_oh, plan.spec, persona, turn_id, language, t0), "meta": {"spec": None}}

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
    from app.auth import PERSONA_DIRECTORY, get_active_principal
    eff_principal = principal or get_active_principal()
    if eff_principal is not None and getattr(eff_principal, "emp_id", None):
        self_emp_id = str(eff_principal.emp_id)
    else:
        self_emp_id = (PERSONA_DIRECTORY.get(persona) or {}).get("emp_id")
    try:
        compiled = compiler.compile(spec, self_emp_id=self_emp_id)
        # B3.3 / SPEC-06 pre-query policy on the compiled spec (data classes of metric + roster columns)
        # and on the question's topic (pay / APAR / vigilance / self ...).
        from app.access_control import UnknownPersona
        try:
            policy = decide(
                persona,
                compiled.data_classes,
                query,
                self_emp_id=self_emp_id if (spec.self_scope or "self" in compiled.data_classes) else None,
                spec=spec,
            )
        except UnknownPersona:
            if spec.self_scope or "self" in compiled.data_classes:
                raise
            policy = decide("E1_HR", compiled.data_classes, query, spec=spec)
        if policy.action == "refuse":
            return {"contract": _refusal_contract(policy, spec, persona, turn_id, language, t0), "meta": {"spec": None}}
        downgraded_from_row = bool(policy.action == "aggregate" and spec.grain == "row")
        is_partial_director = bool(policy.persona_class == "director" and downgraded_from_row)
        if policy.action == "aggregate" and downgraded_from_row and not is_partial_director:
            spec = to_aggregate(spec)
            compiled = compiler.compile(spec, self_emp_id=self_emp_id)
            status.append("RBAC: names restricted for this role; answering with aggregate counts (D-11)")
        if _is_junior(persona) and compiled.grain == "aggregate" and not spec.self_scope:
            compiled = compiler.compile(spec, cell_count=True, self_emp_id=self_emp_id)  # per-cell population for suppression
        result = await compiler.execute(compiled)
    except UnknownPersona:
        raise
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
    raw_rows_before_k5 = [dict(r) for r in rows]
    
    if is_partial_director:
        my_func = policy.function
        out_rows = []
        collapsed = {}
        for r in raw_rows_before_k5:
            disc = str(r.get("discipline") or "").upper()
            row_func = "FIN" if "FIN" in disc else "HR"
            if row_func == my_func:
                out_rows.append(r)
            else:
                g = str(r.get("grade") or "UNKNOWN")
                collapsed[g] = collapsed.get(g, 0) + 1
        for g, count in collapsed.items():
            func_lbl = "Finance" if my_func == "HR" else "HR/Corp"
            out_rows.append({"grade": g, "name": f"{count} {g} employees ({func_lbl})"})
        rows = out_rows
        status.append("RBAC: partial roster (D-43); out-of-function rows collapsed")

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
    if compiled.grain == "aggregate" and (not compiled.dims or len(rows) == 1) and rows and (not junior or compiled.definition_id):
        breakdown = await _companion_breakdown(spec, compiled, compiler, junior=junior)
    await asyncio.sleep(0)
    visual = build_visual(spec, compiled, columns, rows, plan.chart_kind, title, subtitle, mode, n_total,
                          breakdown=breakdown, persona=persona, query=query, raw_rows=raw_rows_before_k5)
    val_col = compiled.value_columns[0] if compiled.value_columns else None
    def _num(v):
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0
    raw_total = sum(_num(r.get(val_col)) for r in raw_rows_before_k5) if val_col else n_total
    
    chart_rows = visual.get("table", {}).get("rows") or rows
    source_for_insights = raw_rows_before_k5 if is_partial_director else chart_rows
    insight_rows = [
        r for r in source_for_insights 
        if str(r.get("grade", "")).strip().upper() not in ("CMD", "DIR")
        and not (str(r.get("grade", "")).strip().upper() == "GRP-B" and _num(r.get(val_col)) == 0)
    ]
    headline = narrate(spec, compiled, columns, insight_rows, n_total=raw_total)
    # B4: deterministic insights (+ previous-FY comparison where the subject has fiscal years),
    # drill-down chips, and a narrator limited to computed facts with a numeric-grounding check.
    prev_rows = await _previous_period_rows(spec, compiled, compiler)
    await asyncio.sleep(0)
    insights = compute_insights(build_insight_context(spec, compiled, insight_rows, raw_total, prev_rows,
                                                      scope_phrases(spec, compiled), query=query))
    extra_nums = derived_numbers(compiled, insight_rows, n_total)
    if breakdown and breakdown[1]:
        for br in breakdown[1]:
            for bv in br.values():
                if isinstance(bv, (int, float)) and not isinstance(bv, bool):
                    extra_nums.append(float(bv))
    allowed = allowed_numbers(rows, insights, spec, extra=extra_nums)
    told = compose_spoken(headline, insights, allowed, language=language)
    spoken = told["text"]

    # BEH-07.33 T1: Voice ASR normalization notice when 'NYC' was spoken for 'ONGC'
    if re.search(r"\bnyc\b", query or "", re.I):
        spoken = "I heard 'NYC' as ONGC. " + spoken

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
    elif (
        spec.metric in ("pnl_statement", "balance_sheet", "cash_flow_statement", "financial_ratios")
        and re.search(r"(?<![-\d/])\b(201[7-9]|202[0-6])\b(?![-\d/])", query or "")
        and not re.search(r"\bfy\s*20\d{2}\b", query or "", re.I)
    ):
        m_cal = re.search(r"(?<![-\d/])\b(201[7-9]|202[0-6])\b(?![-\d/])", query or "")
        if m_cal:
            yyyy = int(m_cal.group(1))
            spoken += f" Taking {yyyy} as FY {yyyy-1}-{yyyy%100:02d}; say FY{(yyyy+1)%100:02d} for {yyyy}-{(yyyy+1)%100:02d}."

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
    if visual.get("note") or visual.get("bridge_error"):
        note_text = str(visual.get("note_hi" if language == "hi" else "note") or visual.get("note") or "").strip()
        if note_text:
            spoken = note_text
            notes = [note_text] + notes
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
    if visual.pop("_designation_fallback", False):
        notes.append("Designation shown from grade title where functional post title is not recorded in HR master.")

    # SPEC-07 §4.2 / BEH-02.02–.03: canonical >5-yr definition KPIs, rule sentence, and policy citations
    v19_sources: List[Dict[str, Any]] = []
    if compiled.definition_id in ("DELHI_GT5_CONT_V1", "STATION_GT5_CONT_V1") and compiled.grain == "aggregate":
        from app.brain.presenter import _station_short_name
        st_short = _station_short_name(compiled.station_wc_id)
        n_gt5_exec, n_gt5_all = await _v19_sibling_counts(spec, compiled, compiler, raw_rows_before_k5)
        rule_line = f"Continuous stay at the current station, more than 5.0 years, as of {get_semantic_model().anchor_date}"
        jrtp_line = "JRTP Rev 4 cl. 3.2 — rotation after 3–5 years (**Illustrative**)"
        hc_line = "Delhi High Court (2018), ONGC v. B.V. Srihari Rao"
        v19_sources = [
            {
                "kind": "policy",
                "doc_id": "POL-JRTP-2024",
                "title": jrtp_line,
                "clause_ref": "JRTP Rev 4 cl. 3.2",
                "source_type": "reconstruction",
            },
            {
                "kind": "policy",
                "doc_id": "J-03",
                "title": hc_line,
                "clause_ref": "W.P.(C) 2018",
                "source_type": "official",
            },
        ]
        if n_gt5_exec is not None and n_gt5_all is not None and not downgraded_from_row:
            if compiled.all_cadres:
                kpi_main = {
                    "label": f"{n_gt5_all} staff > 5 yrs continuous in {st_short} (all cadres)",
                    "value": n_gt5_all,
                    "unit": "employees",
                    "delta": f"{n_gt5_exec} executives ({n_gt5_all} including non-executive staff)",
                }
                lead_t2 = (
                    f"Across all cadres in {st_short}, {n_gt5_all} employees "
                    f"({n_gt5_exec} executives and {n_gt5_all - n_gt5_exec} non-executive staff) "
                    f"have more than 5 years of continuous stay."
                )
            else:
                kpi_main = {
                    "label": f"{n_gt5_exec} executives ({n_gt5_all} including non-executive staff)",
                    "value": n_gt5_exec,
                    "unit": "executives",
                    "delta": f"{n_gt5_exec} executives ({n_gt5_all} including non-executive staff) · > 5 yrs continuous in {st_short}",
                }
                lead_t2 = (
                    f"In {st_short}, **{n_gt5_exec} executives** ({n_gt5_all} including non-executive staff) "
                    f"have been posted for more than 5 years."
                )
            existing_kpis = [k for k in (visual.get("kpis") or []) if k.get("label") != kpi_main["label"]]
            visual["kpis"] = [kpi_main] + existing_kpis[:2]
            spoken = (
                f"{lead_t2} Rule: {rule_line} (> 1,826 days; {get_semantic_model().anchor_date}). "
                f"Policy: {jrtp_line}; {hc_line}. The level-wise column chart is on screen."
            )

    ins_texts = [i.text for i in insights][:4] or [s for s in headline.split(". ") if s and "on screen" not in s][:3]
    ins_v2_list = [i.to_contract() for i in insights][:6]
    if (
        compiled.subject == "workforce"
        and [alias for _, alias in compiled.dims] == ["grade"]
        and not compiled.definition_id
        and "largest executive level" in str(visual.get("title") or "")
        and visual["title"] not in ins_texts
    ):
        ins_texts = [visual["title"]] + ins_texts[:3]
        ins_v2_list = [{"kind": "headline", "text": visual["title"]}] + ins_v2_list[:5]
    if compiled.definition_id in ("DELHI_GT5_CONT_V1", "STATION_GT5_CONT_V1") and compiled.grain == "aggregate" and not downgraded_from_row:
        rule_ins = f"Continuous stay at the current station, more than 5.0 years, as of {get_semantic_model().anchor_date}"
        cite_ins = "JRTP Rev 4 cl. 3.2 — rotation after 3–5 years (**Illustrative**) · Delhi High Court (2018), ONGC v. B.V. Srihari Rao"
        ins_texts = [ins_texts[0] if ins_texts else spoken, rule_ins, cite_ins] + ins_texts[1:2]
        ins_v2_list = [
            {"kind": "headline", "text": ins_texts[0]},
            {"kind": "note", "text": rule_ins},
            {"kind": "note", "text": cite_ins},
        ] + ins_v2_list[:3]

    if language == "hi":
        from app.brain.narrator import translate_to_hindi
        spoken = translate_to_hindi(spoken)
    elif language == "hi-en":
        from app.brain.narrator import translate_to_hinglish
        spoken = translate_to_hinglish(spoken)

    contract: Dict[str, Any] = {
        "turn_id": turn_id,
        "language": language,
        "persona": persona,
        "spoken_summary": spoken,
        "display_text": spoken[:600],
        "visual": visual,
        "insights": ins_texts[:4],
        "insights_v2": ins_v2_list[:6],
        "drilldowns": make_drilldowns(spec, persona, compiled.grain, max_n=4 if (compiled.definition_id or compiled.metric in ("pnl_statement", "balance_sheet", "cash_flow_statement", "financial_ratios")) else 3),
        "sources": sources_list + v19_sources + (
            [{"kind": "policy", "object": "financial_build snapshot (unverified; real AR data pending)", "clause_ref": "hrfin_docs.financial_notes_chunks"}]
            if is_legacy and (compiled.subject == "corporate" or compiled.metric in ("pnl_statement", "balance_sheet", "cash_flow_statement", "financial_ratios")) else []
        ),
        "suggestions": [],
        "access": {
            "status": "allowed",
            **({"self_emp_id": policy.self_emp_id} if (policy and policy.self_emp_id and "self" in compiled.data_classes) else {}),
            **(
                {"allow_pay_aggregate": True}
                if (
                    policy
                    and compiled.grain == "aggregate"
                    and "pay_aggregate" in policy.data_classes
                    and "pay_individual" not in policy.data_classes
                    and "named" not in policy.data_classes
                    and policy.action == "allow"
                    and not any(f.field in ("emp_id", "name", "emp_name") for f in spec.filters)
                    and set(spec.dimensions) <= {"grade", "discipline", "wc", "asset", "fy"}
                )
                else {}
            ),
            **({"target_function": policy.target_function} if (policy and policy.target_function) else {}),
            **({"data_classes": policy.data_classes} if (policy and policy.data_classes) else {}),
        },
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
        **({"definition_id": compiled.definition_id} if compiled.definition_id else {}),
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
    if is_partial_director:
        contract["access"] = {
            "status": "partial",
            "code": "R-FUNC",
            "reason": "Director function-scope logic applied (D-43).",
            "rule_ref": "D-43"
        }
        if isinstance(tbl, dict):
            tbl["masking"] = {
                "level": "aggregate",
                "code": "R-FUNC",
                "masked_columns": ["name", "emp_id"],
                "reason": "Director function-scope logic applied (D-43).",
                "rule_ref": "D-43",
            }
        
        my_func_lbl = "Finance & Accounts" if policy.function == "FIN" else "HR/Corp"
        n_named = sum(1 for r in out_rows if "emp_id" in r and r["emp_id"])
        n_collapsed = len(raw_rows_before_k5) - n_named
        lead = f"Showing named records for {my_func_lbl} ({n_named}); other disciplines are summarised by grade ({n_collapsed}) under D-43. "
        contract["spoken_summary"] = lead + contract["spoken_summary"]
        contract["display_text"] = contract["spoken_summary"][:590]
    elif policy is not None and policy.action == "aggregate" and (
        downgraded_from_row
        or (policy.code in ("R-SENS", "R-FUNC") and "general_hr" not in (policy.data_classes or []))
    ):
        from app.answer_composer import render_refusal_copy
        agg_code = policy.code or "R-NAMED"
        rc = render_refusal_copy(agg_code, lang=language, persona=persona)
        contract["access"] = {
            "status": "partial",
            "code": agg_code,
            "reason": rc["text"],
            "rule_ref": policy.rule_ref or rc["rule_ref"],
            "alternative": rc["alternative"],
            "alternatives": rc["alternatives"],
        }
        if isinstance(tbl, dict):
            tbl["masking"] = {
                "level": "aggregate",
                "code": agg_code,
                "masked_columns": ["name", "emp_id"],
                "reason": rc["text"],
                "rule_ref": policy.rule_ref or rc["rule_ref"],
            }
        lead = rc["text"] + " "
        contract["spoken_summary"] = lead + contract["spoken_summary"]
        contract["display_text"] = contract["spoken_summary"][:590]
    elif policy is not None and policy.action == "aggregate":
        contract["access"] = {
            "status": "partial",
            "code": "R-K5" if suppressed else (policy.code or "R-FUNC"),
            "reason": policy.reason or "Aggregate counts shown for your role (D-11 / D-43).",
            "rule_ref": policy.rule_ref or "D-11",
        }
        if isinstance(tbl, dict):
            tbl["masking"] = {
                "level": "aggregate",
                "code": contract["access"]["code"],
                "reason": contract["access"]["reason"],
                "rule_ref": contract["access"]["rule_ref"],
            }
    elif isinstance(tbl, dict):
        tbl["masking"] = {"level": "none"}
    if suppressed and isinstance(tbl, dict):
        from app.answer_composer import render_refusal_copy
        rc_k5 = render_refusal_copy("R-K5", lang=language, persona=persona)
        if not downgraded_from_row:
            tbl.setdefault("masking", {"level": "aggregate"})
            tbl["masking"]["level"] = "aggregate"
            tbl["masking"]["code"] = "R-K5"
            tbl["masking"]["reason"] = f"{suppressed} cell(s) below 5 shown as <5 (D-11 small-cell rule)"
            tbl["masking"]["rule_ref"] = "D-11"
        if contract["access"]["status"] == "allowed":
            contract["access"] = {
                "status": "partial",
                "code": "R-K5",
                "reason": f"{suppressed} cell(s) below 5 shown as <5 (D-11 small-cell rule)",
                "rule_ref": "D-11",
                "alternative": rc_k5["alternative"],
                "alternatives": rc_k5["alternatives"],
            }
        note = "Groups under 5 people are shown as <5 and left out of totals (D-11)."
        contract["caveat"] = (contract.get("caveat", "") + "; " if contract.get("caveat") else "") + note
        if note not in contract["spoken_summary"] and "shown as '<5'" not in contract["spoken_summary"]:
            contract["spoken_summary"] = contract["spoken_summary"].rstrip() + " Groups under 5 people are shown as <5."
            contract["display_text"] = contract["spoken_summary"][:590]
    if compiled.grain == "row" and isinstance(tbl, dict):
        actions = row_actions(persona, compiled.subject)
        if actions:
            tbl["row_actions"] = actions

    # D-66: stamp synthetic HR label on any allowed/partial contract exposing EMP-000001..3 personal HR fields
    apply_office_holder_safeguard(contract, persona, query=query)

    # B3/B4 hooks (RBAC masking, insights, drill-downs) are applied by the caller via `postprocess`.
    meta = {"compiled": compiled, "result": result, "columns": columns, "rows": rows, "code_maps": code_maps,
            "plan": plan, "spec": spec, "policy": policy}
    return {"contract": contract, "meta": meta}


async def _v19_sibling_counts(
    spec: QuerySpec,
    compiled: Any,
    compiler: Any,
    raw_rows: List[Dict[str, Any]],
) -> tuple[Optional[int], Optional[int]]:
    """Computes `(n_gt5_exec, n_gt5_all)` for `DELHI_GT5_CONT_V1` / `STATION_GT5_CONT_V1` from SQL."""
    from app.brain.presenter import EXEC_LEVELS
    from app.brain.query_spec import Filter

    val_col = compiled.value_columns[0] if compiled.value_columns else "headcount"
    cur_total = int(
        round(
            sum(
                float(r.get(val_col) or 0)
                for r in raw_rows
                if isinstance(r.get(val_col), (int, float)) and not isinstance(r.get(val_col), bool)
            )
        )
    )
    try:
        if compiled.all_cadres:
            n_all = cur_total
            if any(alias == "grade" for _, alias in (compiled.dims or [])):
                n_exec = int(
                    round(
                        sum(
                            float(r.get(val_col) or 0)
                            for r in raw_rows
                            if str(r.get("grade") or "").upper() in EXEC_LEVELS
                            and isinstance(r.get(val_col), (int, float))
                            and not isinstance(r.get(val_col), bool)
                        )
                    )
                )
                return n_exec, n_all
            exec_filters = [f for f in (spec.filters or []) if f.field != "cadre"] + [
                Filter(field="cadre", op="=", value="executive")
            ]
            exec_spec = spec.model_copy(update={"dimensions": [], "filters": exec_filters})
            exec_cq = compiler.compile(exec_spec)
            exec_res = await compiler.execute(exec_cq)
            n_exec = (
                int(round(float(exec_res.rows[0].get(val_col) or cur_total)))
                if exec_res.rows
                else cur_total
            )
            return n_exec, n_all
        else:
            n_exec = cur_total
            all_filters = [f for f in (spec.filters or []) if f.field != "cadre"] + [
                Filter(field="cadre", op="=", value="all")
            ]
            all_spec = spec.model_copy(update={"dimensions": [], "filters": all_filters})
            all_cq = compiler.compile(all_spec)
            all_res = await compiler.execute(all_cq)
            n_all = (
                int(round(float(all_res.rows[0].get(val_col) or cur_total)))
                if all_res.rows
                else cur_total
            )
            return n_exec, n_all
    except Exception as e:
        logger.info(f"v19 sibling count fallback: {e}")
        return cur_total, cur_total


async def _companion_breakdown(spec: QuerySpec, compiled, compiler, junior: bool = False) -> Optional[Any]:
    """For 0-dimension scalar counts/totals, fetch a natural 1-dimension breakdown so a plot is always shown."""
    from app.brain.semantic_model import get_semantic_model
    sm = get_semantic_model()
    subj = sm.subjects.get(compiled.subject)
    if not subj:
        return None
    filter_fields = {f.field for f in spec.filters}
    if compiled.definition_id in ("DELHI_GT5_CONT_V1", "STATION_GT5_CONT_V1"):
        candidates = ["grade", "discipline", "wc"]
    else:
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
        if junior and bd_cols:
            bd_rows, _ = suppress_small_cells(bd_rows, _count_columns(bd_cq), by_name=False)
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


def _refusal_contract(policy, spec: Optional[QuerySpec], persona: str, turn_id: str, language: str, t0: float) -> Dict[str, Any]:
    """Refusal card for a planner question the policy refuses (SPEC-06 §4.6 / P2H.2); never ships granular data."""
    from app.answer_composer import build_refusal_contract

    code = policy.code or "R-NAMED"
    return build_refusal_contract(
        code=code,
        persona=persona,
        turn_id=turn_id,
        language=language,
        rule_ref=policy.rule_ref,
        query_spec=spec.to_contract() if spec is not None else None,
        latency_ms=round((time.perf_counter() - t0) * 1000, 2),
    )


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
    spoken = f"Here is the same data as a {kind.replace('_', ' ')}. Details are on screen."
    if language == "hi":
        from app.brain.narrator import translate_to_hindi
        spoken = translate_to_hindi(spoken)
    elif language == "hi-en":
        from app.brain.narrator import translate_to_hinglish
        spoken = translate_to_hinglish(spoken)
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
