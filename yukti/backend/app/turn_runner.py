"""ADK Agent Turn Execution Engine for Yukti AI.
Drives text-based turns through Google ADK Runner and Gemini models:
1. Intercepts restricted queries via AccessCheckHook (CDA Rule 5.0 / JRTP Clause 11.0).
2. Executes live LLM turn: the model analyzes the prompt, chooses tools, and writes BigQuery SQL.
3. Captures tool events, generated SQL, BigQuery records, and synthesized spoken responses.
4. Formats and validates the canonical Answer Contract JSON.
"""

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from app.access_control import check_access, normalize_persona
from app.agent import create_yukti_agent
from app.answer_composer import detect_language, get_contract_validator, validate_and_repair_contract
from app.brain.semantic_model import get_semantic_model
from app.brain.pipeline import planner_enabled, run_planner_turn
from app.config import DEFAULT_TEXT_MODEL, GCP_PROJECT, VERTEX_TEXT_LOCATION
from app.router import get_semantic_router
from app.semantic.entities import get_entities
from app.session_memory import get_session_manager
from app.tools.chart_rules import (
    build_chart_spec,
    extract_requested_chart_kind,
    is_pure_replot_request,
    select_chart_kind,
)

logger = logging.getLogger("yukti.turn_runner")

# P0.1 (BUG-33): user-facing error copy. E-AUTH from SPEC-06 §4.6; generic copy for everything else.
E_AUTH_COPY = {
    "en": "I can't reach the data service right now. Nothing is wrong with your question; please try again in a minute.",
    "hi": "अभी डेटा सेवा से संपर्क नहीं हो पा रहा। कृपया एक मिनट बाद फिर पूछें।",
}
GENERIC_ERROR_COPY = {
    "en": "Something went wrong answering that. Please try again.",
    "hi": "इसका उत्तर देने में कुछ गड़बड़ हो गई। कृपया फिर से कोशिश करें।",
}


def _is_auth_or_outage_error(exc: BaseException) -> bool:
    """RefreshError / DefaultCredentialsError / BigQuery Forbidden, Unauthorized, ServiceUnavailable (incl. chained)."""
    try:
        from google.api_core import exceptions as gexc
        from google.auth import exceptions as aexc
        types_ = (aexc.RefreshError, aexc.DefaultCredentialsError, gexc.Forbidden, gexc.Unauthorized,
                  gexc.ServiceUnavailable)
    except Exception:  # pragma: no cover - libraries always present in the backend venv
        return False
    seen = 0
    cur: Optional[BaseException] = exc
    while cur is not None and seen < 5:
        if isinstance(cur, types_):
            return True
        cur = cur.__cause__ or cur.__context__
        seen += 1
    return False


def safe_error_copy(exc: BaseException, lang: str = "en") -> str:
    """Maps any exception to user-safe text (EN, or HI for Hindi turns). Never includes str(exc)."""
    key = "hi" if lang == "hi" else "en"
    return (E_AUTH_COPY if _is_auth_or_outage_error(exc) else GENERIC_ERROR_COPY)[key]


def make_clean_title_and_subtitle(
    query: str,
    entry_id: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    """Generates templated certified titles and informative work-centre subtitles."""
    q_low = query.lower()
    p = params or {}
    wc_id = p.get("wc_id")

    # 2. City & Work Centre tenure checks (names from the single entity dictionary, B1.2)
    ents = get_entities()
    target_wc = wc_id or ents.resolve_wc(q_low)
    if target_wc and target_wc in ents.work_centres:
        tenure_words = ["stay", "year", "tenure", "saal", "kitne", "officer", "executive", "posted"]
        if wc_id or any(k in q_low for k in tenure_words) or entry_id in ("C1", "H1"):
            a = ents.work_centres[target_wc]
            city = str(a.get("city", ""))
            label = city if city and city.lower() in q_low else ents.wc_name(target_wc)
            full_name = ents.wc_name(target_wc, short=False)
            short_name = ents.wc_name(target_wc)
            if city and city.lower() in short_name.lower() and city.lower() not in full_name.lower():
                full_name = f"{city} {full_name}"  # "Tel Bhavan Corporate Administration" -> "Dehradun Tel Bhavan ..."
            sub = f"Work Centre: {full_name}"
            if a.get("hard_station_cat") == "C":
                sub += " | Station Category C"
            if ents.wc_notes.get(target_wc):
                sub += f" | {ents.wc_notes[target_wc]}"
            return f"{label}: Executives with ≥5 Years' Continuous Stay", f"{sub} | {get_semantic_model().anchor_date}"

    clean = re.sub(r"^(How many|What is the|What are the|Which|Please show|Tell me about)\s+", "", query, flags=re.IGNORECASE).strip().rstrip("?")
    return clean[:65].capitalize(), f"ONGC enterprise records (demo data) | {get_semantic_model().anchor_date}"


def make_clean_title(query: str) -> str:
    t, _ = make_clean_title_and_subtitle(query)
    return t


def replace_codes_with_friendly_names(obj: Any) -> Any:
    """Recursively replaces technical discipline/work-centre/field codes with friendly human names.

    Delegates to the single entity dictionary (`app/semantic/entities.py`, B1.2).
    """
    return get_entities().replace_codes(obj)


class AgentTurnRunner:
    """Manages real LLM turn execution using Google ADK."""

    def __init__(self, model_name: Optional[str] = None, principal: Optional[Any] = None):
        os.environ["GOOGLE_CLOUD_LOCATION"] = VERTEX_TEXT_LOCATION
        self.model_name = model_name or DEFAULT_TEXT_MODEL
        self.session_service = InMemorySessionService()
        self.agent = create_yukti_agent(model_name=self.model_name, principal=principal)
        self.runner = Runner(
            agent=self.agent,
            app_name=self.agent.name,
            session_service=self.session_service,
        )
        self.validator = get_contract_validator()
        self.session_manager = get_session_manager()
        # Pre-warm catalog, entities, RBAC, and insight modules at startup so the first
        # async turn never stalls the event loop on cold module imports or disk I/O (H1.1).
        from app.brain.insight_context import table_insights as _ti  # noqa: F401
        from app.brain.rbac import enforce_contract as _ec  # noqa: F401
        from app.live_session import detect_screen_control_intent as _dsci  # noqa: F401
        from app.semantic.normalize import load_catalog
        get_entities()
        load_catalog()

    def _validate_contract(self, contract: Dict[str, Any]) -> Dict[str, Any]:
        """Validates and repairs a contract so schema drift never causes an unhandled HTTP 500 (H1.3b)."""
        return validate_and_repair_contract(contract)

    def _role_switch_contract(self, query: str, session_state: Any, norm_persona: str, principal: Optional[Any],
                              turn_id: str, det_lang: str, t0: float) -> Dict[str, Any]:
        """P0.4 (BUG-06): answer to a role-switch utterance. Non-admin -> R-ROLE (SPEC-06 §4.6), persona
        unchanged, audit `role_switch_denied`. Admin -> `ui_action: set_persona` for the target persona; the
        API layer issues the new token and audits `admin_persona_switch`."""
        from app.auth import PERSONA_DIRECTORY, Principal, audit, r_role_text, requested_persona

        target = requested_persona(query)
        if principal is not None and principal.is_admin and target:
            spoken = f"Switched the presenter session to {PERSONA_DIRECTORY[target]['designation']}."
            contract = {
                "turn_id": turn_id, "language": det_lang, "persona": target,
                "spoken_summary": spoken, "display_text": spoken,
                "visual": {"type": "none", "mode": "replace"},
                "insights": [], "sources": [{"kind": "policy", "title": "SPEC-06 §4.4 (demo presenter)"}],
                "suggestions": ["What can I ask?"], "access": {"status": "allowed"},
                "export_options": [], "status_events": [f"Admin persona switch requested: {target}"],
                "ui_action": {"command": "set_persona", "value": target},
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            }
            self._validate_contract(contract)
            return contract

        who = principal
        if who is None:  # internal callers without a token: describe the session persona
            info = PERSONA_DIRECTORY.get(norm_persona, {"emp_id": "", "display_name": norm_persona,
                                                        "designation": norm_persona, "function": "", "grade": ""})
            who = Principal(emp_id=info["emp_id"], persona=norm_persona, function=info["function"], grade=info["grade"],
                            display_name=info["display_name"], designation=info["designation"])
        from app.answer_composer import render_refusal_copy
        rc_role = render_refusal_copy(
            "R-ROLE",
            lang=det_lang,
            persona=norm_persona,
            display_name=who.display_name,
            designation=who.designation,
        )
        text = rc_role["text"]
        audit("role_switch_denied", who, turn_id=turn_id, decision="refused", rule_ref="SPEC-06 §4.4 R-ROLE",
              query=query, requested=target)
        contract = {
            "turn_id": turn_id, "language": det_lang, "persona": norm_persona,
            "spoken_summary": text, "display_text": text,
            "visual": {"type": "none", "mode": "replace"},
            "insights": [], "sources": [{"kind": "policy", "title": "SPEC-06 §4.4 (R-ROLE)"}],
            "suggestions": ["What can I ask?"],
            "access": {
                "status": "refused",
                "code": "R-ROLE",
                "reason": "Access level cannot be changed from a conversation.",
                "rule_ref": "SPEC-06 §4.4 R-ROLE",
                "alternative": rc_role["alternative"],
                "alternatives": rc_role["alternatives"],
            },
            "export_options": [], "status_events": ["Role change from conversation refused (R-ROLE)"],
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        }
        self._validate_contract(contract)
        session_state.record_turn(contract, user_query=query)
        return contract

    def _prune_adk_sessions(self, user_id: str, session_id: str, max_sessions: int = 200, max_events: int = 40) -> None:
        """Bounds ADK InMemorySessionService sessions and event history, stripping bulky `all_rows` (H1.3b)."""
        app_map = getattr(self.session_service, "sessions", {}).get(self.runner.app_name, {})
        if not app_map:
            return
        user_map = app_map.get(user_id, {})
        sess = user_map.get(session_id)
        if sess is not None and getattr(sess, "events", None):
            for ev in sess.events:
                if ev.content and ev.content.parts:
                    for part in ev.content.parts:
                        fr = getattr(part, "function_response", None)
                        if fr is not None and isinstance(getattr(fr, "response", None), dict):
                            resp_dict = fr.response
                            resp_dict.pop("all_rows", None)
                            if isinstance(resp_dict.get("result"), dict):
                                resp_dict["result"].pop("all_rows", None)
            if len(sess.events) > max_events:
                trimmed = sess.events[-max_events:]
                while trimmed and getattr(trimmed[0], "content", None) and getattr(trimmed[0].content, "role", None) != "user":
                    trimmed.pop(0)
                if trimmed:
                    sess.events[:] = trimmed

        # Bound total sessions across all personas
        all_entries = [
            (uid, sid, getattr(s_obj, "last_update_time", 0.0))
            for uid, u_sessions in app_map.items()
            for sid, s_obj in u_sessions.items()
        ]
        if len(all_entries) > max_sessions:
            all_entries.sort(key=lambda item: item[2])
            for uid, sid, _ts in all_entries[: len(all_entries) - max_sessions]:
                app_map.get(uid, {}).pop(sid, None)

    async def execute_turn_async(
        self,
        query: str,
        session_id: str,
        persona: str = "CMD",
        language: str = "en",
        voice_override: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        ui_context: Optional[Dict[str, Any]] = None,
        spec_patch: Optional[Dict[str, Any]] = None,
        base_spec: Optional[Dict[str, Any]] = None,
        principal: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Runs a turn, then applies the post-query RBAC guard to the contract (B3.4).

        `enforce_contract` runs on EVERY path (planner, fast paths, legacy LLM): a junior persona
        never receives named / pay / APAR columns, small cells are suppressed, and access.status,
        text and visual agree (consistency rule, FEAT-010).

        P0.4: when `principal` (app.auth.Principal, from the signed session token) is given, its persona
        is the only persona used; nothing in the query or the contract can change it (admins excepted).
        """
        from app.auth import principal_for_persona, reset_active_principal, set_active_principal

        if principal is not None:
            persona = principal.persona
        else:
            principal = principal_for_persona(persona)
        token = set_active_principal(principal)
        
        # Ensure runner is bound to correct agent after principal is set
        self.agent = create_yukti_agent(model_name=self.model_name, principal=principal)
        self.runner.agent = self.agent

        try:
            contract = await self._execute_turn_inner(
                query=query, session_id=session_id, persona=persona, language=language,
                voice_override=voice_override, history=history, ui_context=ui_context,
                spec_patch=spec_patch, base_spec=base_spec, principal=principal,
            )
        finally:
            reset_active_principal(token)
        from app.brain.rbac import enforce_contract, persona_class
        req_persona = normalize_persona(persona)
        # P0.4 (BUG-06): the persona is never taken from the contract (that let a free-text "switch role"
        # widen access). Only an admin's explicit switch (ui_action set_persona, issued by the deterministic
        # role-switch handler) may change it; everyone else is enforced and stamped with the session persona.
        ui_act = contract.get("ui_action") or {}
        if principal is not None and principal.is_admin and ui_act.get("command") == "set_persona" and contract.get("persona"):
            persona_eff = contract["persona"]
        else:
            persona_eff = req_persona
            contract["persona"] = req_persona
        contract = enforce_contract(contract, persona_eff)
        if (
            persona_class(persona_eff) == "junior"
            or persona_eff == "DIR_FIN"
            or (contract.get("access") or {}).get("status") != "allowed"
        ):
            self._sync_session_after_enforce(session_id, contract)
        # B4: legacy-path data answers also carry deterministic insights (computed from the table
        # actually shown, after RBAC masking) so every data answer has insights_v2.
        vis = contract.get("visual") or {}
        tbl = vis.get("table") or {}
        if (not contract.get("insights_v2") and vis.get("type") in ("chart", "table", "kpi")
                and contract.get("access", {}).get("status") != "refused" and tbl.get("rows")):
            try:
                from app.brain.insight_context import table_insights
                ins = table_insights(tbl.get("columns") or [], tbl.get("rows") or [])
                if ins:
                    contract["insights_v2"] = [i.to_contract() for i in ins][:6]
            except Exception as e_ins:
                logger.info(f"legacy insights skipped: {e_ins}")
        self._validate_contract(contract)
        try:
            from app.export_audit import register_turn_contract

            emp_id = getattr(principal, "emp_id", "") if principal is not None else ""
            if not emp_id:
                emp_id = PERSONA_DIRECTORY.get(persona_eff, {}).get("emp_id", "")
            sess_st = self.session_manager.get_or_create_session(session_id, persona=persona_eff)
            sess_st.emp_id = emp_id
            if sess_st.turns and sess_st.turns[-1].get("turn_id") == contract.get("turn_id"):
                sess_st.turns[-1]["emp_id"] = emp_id
            register_turn_contract(
                turn_id=str(contract.get("turn_id") or ""),
                contract=contract,
                emp_id=emp_id,
                persona=persona_eff,
                session_id=session_id,
            )
        except Exception as e_reg:
            logger.debug(f"turn export registration skipped: {e_reg}")
        return contract

    async def _execute_turn_inner(
        self,
        query: str,
        session_id: str,
        persona: str = "CMD",
        language: str = "en",
        voice_override: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        ui_context: Optional[Dict[str, Any]] = None,
        spec_patch: Optional[Dict[str, Any]] = None,
        base_spec: Optional[Dict[str, Any]] = None,
        principal: Optional[Any] = None,
    ) -> Dict[str, Any]:
        os.environ["GOOGLE_CLOUD_LOCATION"] = VERTEX_TEXT_LOCATION
        t0 = time.perf_counter()
        from app.brain.planner import normalize_asr_query
        query = normalize_asr_query(query)
        norm_persona = normalize_persona(persona)
        det_lang = detect_language(query, default=language)

        session_state = self.session_manager.get_or_create(
            session_id=session_id,
            persona=norm_persona,
            language=det_lang,
            emp_id=getattr(principal, "emp_id", None),
        )
        session_state.hydrate_from_client_history(history=history, ui_context=ui_context)
        session_state.ensure_principal(norm_persona, getattr(principal, "emp_id", None))

        turn_index = len(session_state.turns) + 1
        turn_id = f"turn-{session_id}-{turn_index:03d}"

        from app.auth import is_role_switch_request
        from app.live_session import detect_screen_control_intent as _sc_detect
        from app.ui_control import SCREEN_CANONICAL_QUERIES
        query_normalized = query.strip().lower().rstrip("?!.")
        _sc_probe = _sc_detect(query_normalized)
        if is_role_switch_request(query) or (_sc_probe and _sc_probe.get("command") == "set_persona"):
            return self._role_switch_contract(query, session_state, norm_persona, principal, turn_id, det_lang, t0)

        if _sc_probe and _sc_probe.get("command") == "open_screen" and _sc_probe.get("value") in SCREEN_CANONICAL_QUERIES:
            query = SCREEN_CANONICAL_QUERIES[_sc_probe["value"]]
            query_normalized = query.strip().lower().rstrip("?!.")
            _sc_probe = None
        elif _sc_probe and _sc_probe.get("command") == "export":
            _sc_probe = None

        requested_chart_kind = extract_requested_chart_kind(query)
        if requested_chart_kind == "waterfall":
            from app.semantic.normalize import resolve_fy as _resolve_fy_early

            prev_vis_m1 = session_state.get_last_visual() or {}
            prev_rows_m1 = session_state.last_rows or (prev_vis_m1.get("table") or {}).get("rows") or []
            prev_stmt_m1 = prev_vis_m1.get("statement") if isinstance(prev_vis_m1.get("statement"), dict) else None
            prev_stmt_periods = [str(p) for p in (prev_stmt_m1.get("periods") or []) if p] if prev_stmt_m1 else []
            fy_early_res = _resolve_fy_early(query)
            req_fy_early = fy_early_res.get("fy") if isinstance(fy_early_res, dict) and fy_early_res.get("fy") else (fy_early_res if isinstance(fy_early_res, str) else None)

            if req_fy_early and not (isinstance(fy_early_res, dict) and fy_early_res.get("from")):
                if prev_stmt_m1 and prev_stmt_m1.get("statement") == "pnl" and req_fy_early in prev_stmt_periods:
                    _sc_probe = {"action": "chart_kind", "command": "set_chart_kind", "value": "waterfall"}
                else:
                    _sc_probe = None
            elif _sc_probe is None:
                is_single_kpi_on_screen = prev_vis_m1.get("type") in ("kpi", "none", None) and len(prev_rows_m1) <= 1
                is_single_metric_wf = bool(
                    re.search(r"(टोटल\s+रेवेन्यू|कुल\s+रेवेन्यू|total\s+revenue|रेवेन्यू\s+का\s+वॉटरफॉल|रेवेन्यू\s+का\s+वाटरफॉल)", query_normalized)
                    and not re.search(r"\b(pat|pbt|profit|pnl|p&l|statement|bridge|income\s+statement)\b|लाभ|प्रॉफिट", query_normalized)
                )
                if is_single_metric_wf and is_single_kpi_on_screen:
                    _sc_probe = {"action": "chart_kind", "command": "set_chart_kind", "value": "waterfall"}
        elif _sc_probe and _sc_probe.get("command") == "set_chart_kind" and not is_pure_replot_request(query):
            _sc_probe = None

        # 0. Clarify rule for FY
        from app.config import v3_field_enabled
        if v3_field_enabled("clarify") or os.getenv("YUKTI_CLARIFY_TEST", "0") == "1":
            last_turn = session_state.turns[-1] if getattr(session_state, "turns", None) else {}
            clarify = last_turn.get("clarify") or last_turn.get("contract", {}).get("clarify") if last_turn else None
            if isinstance(clarify, dict) and clarify.get("slot") == "fiscal_period":
                pending_spec = clarify.get("pending_spec")
                if pending_spec:
                    from app.semantic.normalize import resolve_fy, last_complete_fy, fy_of, fy_label, ANCHOR_DATE
                    from app.brain.coverage import get_financial_coverage_fys
                    avail = get_financial_coverage_fys()
                    latest = avail[-1] if avail else last_complete_fy()
                    prev = avail[-2] if len(avail) >= 2 else fy_label(fy_of(ANCHOR_DATE) - 2)
                    y5 = avail[-5] if len(avail) >= 5 else fy_label(fy_of(ANCHOR_DATE) - 5)
                    y10 = avail[-10] if len(avail) >= 10 else fy_label(fy_of(ANCHOR_DATE) - 10)
                    
                    fy_resolved = None
                    if re.search(r"\b(five years|5 saal|last 5|5-year trend)\b", query_normalized):
                        fy_resolved = {"from": y5, "to": latest}
                    elif re.search(r"\b(ten years|decade|10 saal|10-year summary)\b", query_normalized):
                        fy_resolved = {"from": y10, "to": latest}
                    elif re.search(r"\b(present year|this year|current|latest|is saal|fy26 \(latest\))\b", query_normalized):
                        fy_resolved = {"fy": latest}
                    elif re.search(r"\b(last year|previous year|pichhle saal|fy25)\b", query_normalized):
                        fy_resolved = {"fy": prev}
                    elif ".." in query_normalized:
                        parts = query_normalized.split("..")
                        fy_resolved = {"from": parts[0].strip().upper(), "to": parts[1].strip().upper()}
                    
                    if not fy_resolved:
                        fy_resolved = resolve_fy(query, available=avail)
                        if isinstance(fy_resolved, str):
                            fy_resolved = {"fy": fy_resolved}
                    
                    if fy_resolved:
                        if fy_resolved.get("fy"):
                            pending_spec["period"] = {"fy": fy_resolved["fy"]}
                        elif fy_resolved.get("from") and fy_resolved.get("to"):
                            pending_spec["period"] = {"from": fy_resolved["from"], "to": fy_resolved["to"]}
                        from app.brain.query_spec import QuerySpec
                        spec_override = QuerySpec.from_contract(pending_spec)
                        planned = await run_planner_turn(query, session_state, norm_persona, turn_id, det_lang, t0, spec_override=spec_override)
                        if planned:
                            return self._finalize_planner_contract(planned, session_state, query, t0)

        # Deterministic Intents
        if _sc_probe:
            from app.intents.ui_control import handle_ui_control
            contract = handle_ui_control(query, session_state, norm_persona, det_lang, turn_id, t0, _sc_probe)
            if contract:
                self._validate_contract(contract)
                session_state.record_turn(contract, user_query=query)
                return contract

        # Access check before data/policy/agent execution (SPEC-11 §4 #2)
        access_dec = check_access(persona=norm_persona, query=query)
        if access_dec.status == "refused":
            from app.answer_composer import _infer_refusal_code, build_refusal_contract
            ref_code = access_dec.code or _infer_refusal_code(
                {"reason": access_dec.reason, "rule_ref": access_dec.rule_ref}
            )
            refusal_contract = build_refusal_contract(
                code=ref_code,
                persona=norm_persona,
                turn_id=turn_id,
                language=det_lang,
                rule_ref=access_dec.rule_ref,
                latency_ms=(time.perf_counter() - t0) * 1000,
            )
            if access_dec.alternative_sql:
                refusal_contract["sources"].append(
                    {"kind": "data", "object": "hrfin_silver.dim_grade", "sql": access_dec.alternative_sql}
                )
            self._validate_contract(refusal_contract)
            session_state.record_turn(refusal_contract)
            return refusal_contract

        from app.intents.greeting import handle_greeting
        greeting_contract = handle_greeting(query, session_state, norm_persona, det_lang, turn_id, t0)
        if greeting_contract:
            self._validate_contract(greeting_contract)
            session_state.record_turn(greeting_contract, user_query=query)
            return greeting_contract

        # P5.3 Coverage intent
        try:
            from app.intents.coverage import handle_coverage
            coverage_contract = handle_coverage(query, session_state, norm_persona, det_lang, turn_id, t0)
            if coverage_contract:
                self._validate_contract(coverage_contract)
                session_state.record_turn(coverage_contract, user_query=query)
                return coverage_contract
        except ImportError:
            pass

        from app.intents.policy import handle_policy
        policy_contract = handle_policy(query, session_state, norm_persona, det_lang, turn_id, t0)
        if policy_contract:
            self._validate_contract(policy_contract)
            session_state.record_turn(policy_contract, user_query=query)
            return policy_contract

        # Transfer note drafting from active cohort/row action (SPEC-07)
        from app.brain.documents import is_transfer_note_request, transfer_note_contract
        if is_transfer_note_request(query):
            try:
                tn = await transfer_note_contract(
                    query, session_state, norm_persona, turn_id, det_lang, t0,
                    ui_context=ui_context, spec_patch=spec_patch,
                )
                if tn is not None:
                    self._validate_contract(tn)
                    session_state.record_turn(tn, user_query=query)
                    return tn
            except Exception as e_tn:
                logger.exception(f"Transfer note drafting failed; falling back: {e_tn}")

        # Coordinator / Planner
        from app.agents.coordinator import route_turn
        coord_res = await route_turn(query, norm_persona, session_state)
        if "contract" in coord_res:
            res_contract = coord_res["contract"]
            self._validate_contract(res_contract)
            session_state.record_turn(res_contract, user_query=query)
            return res_contract

        if coord_res.get("proposed_action") or coord_res.get("access", {}).get("status") == "refused":
            contract = {
                "contract_version": 3,
                "turn_id": turn_id,
                "language": det_lang,
                "persona": norm_persona,
                "spoken_summary": coord_res.get("answer", "Action proposed."),
                "display_text": coord_res.get("answer", "Action proposed."),
                "visual": {"type": "none", "mode": "replace"} if "access" not in coord_res else {"type": "refusal", "mode": "replace"},
                "insights": [],
                "sources": [],
                "suggestions": ["Proceed", "Cancel"],
                "access": coord_res.get("access", {"status": "allowed"}),
                "export_options": [],
                "status_events": ["Proposed action"],
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            }
            if coord_res.get("proposed_action"):
                contract["proposed_action"] = coord_res["proposed_action"]
            if coord_res.get("ui_action") is not None:
                contract["ui_action"] = coord_res["ui_action"]
            if coord_res.get("alternative"):
                contract["alternative"] = coord_res["alternative"]
            if coord_res.get("rule_ref"):
                contract["rule_ref"] = coord_res["rule_ref"]
                contract["access"] = {
                    "status": "refused",
                    "reason": coord_res.get("answer"),
                    "rule_ref": coord_res["rule_ref"],
                    "alternative": coord_res.get("alternative"),
                }
                contract["suggestions"] = ["What can I ask?"]
            self._validate_contract(contract)
            session_state.record_turn(contract, user_query=query)
            return contract
            
        patch_obj, base_obj = None, None
        if spec_patch:
            try:
                from app.brain.query_spec import QuerySpec, SpecPatch
                patch_obj = SpecPatch.model_validate(spec_patch)
                base_obj = QuerySpec.from_contract(base_spec) if base_spec else None
            except Exception:
                pass
                
        try:
            planned = await run_planner_turn(query, session_state, norm_persona, turn_id, det_lang, t0,
                                             patch_override=patch_obj, base_spec=base_obj, principal=principal)
            if planned is not None:
                return self._finalize_planner_contract(planned, session_state, query, t0)
        except Exception as e_plan:
            import logging
            logging.getLogger(__name__).exception(f"Planner pipeline failed: {e_plan}")
            
        session_state.spec_history.append({})
        session_state.spec_history[:] = session_state.spec_history[-20:]

        if os.getenv("YUKTI_LEGACY_AGENT", "0") == "1":
            # Continue on legacy
            self._prune_adk_sessions(norm_persona, session_id)
            tool_responses_recorded = []
            
            async def intercept_tools(e):
                from google.adk.events import ToolCallResultEvent
                if isinstance(e, ToolCallResultEvent):
                    if hasattr(e.content, "parts"):
                        for p in e.content.parts:
                            fr = getattr(p, "function_response", None)
                            if fr and fr.name != "generate_business_insights" and isinstance(getattr(fr, "response", None), dict):
                                tool_responses_recorded.append(fr.response)
                                
            self.runner.add_event_listener(intercept_tools)
            response = await self.runner.run(query, user_id=norm_persona, session_id=session_id)
            self.runner.remove_event_listener(intercept_tools)
            
            contract = self._build_visual_and_sources(
                model_text=response.content.text,
                tool_responses=tool_responses_recorded,
                query=query,
                language=det_lang,
                turn_id=turn_id,
                persona=norm_persona,
                t0=t0,
            )
            return contract
        else:
            # Honest structured response
            contract = {
                "turn_id": turn_id,
                "language": det_lang,
                "persona": norm_persona,
                "spoken_summary": "I couldn't work that out just now. Please try again in a minute. (ref E-PLN-1234)",
                "display_text": "I couldn't work that out just now. Please try again in a minute. (ref E-PLN-1234)",
                "visual": {"type": "none", "mode": "replace"},
                "insights": [],
                "sources": [],
                "suggestions": ["What can you do?", "Show coverage"],
                "access": {"status": "allowed"},
                "export_options": [],
                "status_events": ["Planner could not resolve the query."],
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            }
            self._validate_contract(contract)
            session_state.record_turn(contract, user_query=query)
            return contract

    def _sync_session_after_enforce(self, session_id: str, contract: Dict[str, Any]) -> None:
        """Session memory keeps the ENFORCED contract (masked rows/text), so later turns (drafts,
        re-plots) can never resurface data the persona may not see (G4 B3 B-3)."""
        st = self.session_manager.sessions.get(session_id)
        if not st or not st.turns:
            return
        last = st.turns[-1]
        for k in ("spoken_summary", "display_text", "visual", "insights", "access", "caveat"):
            if k in contract:
                last[k] = contract[k]
            else:
                last.pop(k, None)
        vis = contract.get("visual") or {}
        if st.visual_history:
            st.visual_history[-1] = vis
        tbl = vis.get("table") or {}
        st.last_rows = list(tbl.get("rows") or [])[:2000]
        st.last_columns = list(tbl.get("columns") or [])
        active_cohort = st.get_active_cohort()
        if active_cohort is not None and active_cohort.get("turn_id") == contract.get("turn_id"):
            acc = contract.get("access") or {}
            if acc.get("status") == "refused":
                st.cohorts = [c for c in st.cohorts if c.get("turn_id") != contract.get("turn_id")]
                st.active_cohort_id = st.cohorts[-1]["cohort_id"] if st.cohorts else None
            else:
                mask_lvl = (tbl.get("masking") or {}).get("level") if isinstance(tbl.get("masking"), dict) else None
                active_cohort["rows"] = list(tbl.get("rows") or [])[:2000]
                active_cohort["columns"] = list(tbl.get("columns") or [])
                if mask_lvl == "aggregate":
                    active_cohort["rbac_decision"] = "aggregate"
                active_cohort["visual"] = dict(vis)

    def _finalize_planner_contract(self, planned: Dict[str, Any], session_state: Any, query: str, t0: float) -> Dict[str, Any]:
        """Validates a planner contract and stores the spec for follow-up patches (B2.5)."""
        contract = planned["contract"]
        meta = planned.get("meta") or {}
        contract["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        self._validate_contract(contract)
        rows = meta.get("rows")
        session_state.record_turn(contract, user_query=query, all_rows=rows)
        if meta.get("spec") is not None:
            session_state.spec_history.append(meta["spec"].to_contract())
        else:
            session_state.spec_history.append({})  # refusal: the next follow-up must not patch an older spec
        session_state.spec_history[:] = session_state.spec_history[-20:]
        return contract

    @staticmethod
    def _hinglish_fallback(query: str, tool_responses: List[Dict[str, Any]]) -> str:
        """Roman-script Hinglish summary built only from the first tool result (no hard-coded numbers)."""
        ents = get_entities()
        resp = (tool_responses[0].get("response") if tool_responses else None) or {}
        params = resp.get("params_applied") or {}
        wc = params.get("wc_id") or ents.resolve_wc(query)
        place = ents.wc_name(wc) if wc else ""
        det = resp.get("deterministic_summary")
        det = det if isinstance(det, dict) else {}
        tot = resp.get("total_count") or det.get("total_count") or resp.get("row_count")
        dims = resp.get("dimension_totals") or det.get("dimension_totals") or {}
        disc = dims.get("discipline_id") or dims.get("discipline") or {}
        ranked = sorted(disc.items(), key=lambda kv: kv[1], reverse=True)[:2]
        top = ""
        if ranked:
            top = "Sabse zyada " + " aur ".join(f"{ents.friendly(k)} ({v})" for k, v in ranked) + " mein hain. "
        if tot is None:
            return "Jawab screen par hai. Details screen par hain."
        if resp.get("query_id") == "C1" and params.get("min_stay_days"):
            years = round(int(params["min_stay_days"]) / 12)
            lead = f"{place or 'Is work centre'} mein {years} saal se zyada {tot} executives hain. "
        else:
            lead = (f"{place}: " if place else "") + f"kul {tot} records mile. "
        return (lead + top + "Details screen par hain.").replace("  ", " ")

    @staticmethod
    def _answer_is_cacheable(route_decision: Dict[str, Any], tool_responses: List[Dict[str, Any]]) -> bool:
        """Answer-cache poisoning guard (bug audit 2.6).

        The answer cache is keyed by the router's (certified_id, params). A contract may only be
        stored under that key if the model actually executed that certified query with those
        parameters and got rows back; otherwise an unrelated / failed / free-SQL answer would be
        served to every later asker of the certified question.
        """
        qid = route_decision.get("query_id")
        want = {k: v for k, v in (route_decision.get("extracted_params") or {}).items() if v is not None}
        for tr in tool_responses:
            if tr.get("name") != "run_certified_query":
                continue
            resp = tr.get("response") or {}
            if resp.get("query_id") != qid or resp.get("status") == "error":
                continue
            applied = resp.get("params_applied") or {}
            if any(str(applied.get(k)) != str(v) for k, v in want.items()):
                continue
            if (resp.get("row_count") or len(resp.get("rows") or [])) > 0:
                return True
        return False

    def _extract_spoken_summary(self, model_text: str, language: str) -> str:
        """Extracts 2-3 clean spoken sentences, stripping table/dataset/clause tokens per User Decision."""
        if not model_text:
            return "I couldn't find verified data for that in the data bank, so I won't guess. I can show the closest related figures if you like."

        clean = re.sub(r"```.*?```", "", model_text, flags=re.DOTALL)
        clean = clean.replace("**", "").replace("*", "").replace("#", "").strip()

        # Clean out technical dataset names, table names, and clause references per User Decision
        clean = re.sub(r"(`?hrfin_(?:gold|silver|docs)\.[a-zA-Z0-9_]+`?)", "", clean)
        clean = re.sub(r"\bClause\s+\d+(?:\.\d+)?\b", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"as verified in\s+`?[a-zA-Z0-9_\.]+`?", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"according to (?:enterprise records in|the table)\s+`?[a-zA-Z0-9_\.]+`?", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"Please (?:view|refer to|see|check) (?:the|our)?\s*(?:interactive|accompanying|canvas)?\s*(?:chart|table|dashboard|breakdown|visual|details)[a-zA-Z\s]*(?:\.|$)", "Details are on screen.", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s{2,}", " ", clean).strip()

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]

        if not sentences:
            return clean[:200]
        if len(sentences) == 1:
            return sentences[0] + " Details are on screen."
        elif len(sentences) <= 3:
            return " ".join(sentences)
        else:
            return " ".join(sentences[:3])

    def _build_visual_and_sources(
        self,
        tool_calls: List[Dict[str, Any]],
        tool_responses: List[Dict[str, Any]],
        query: str,
        visual_mode: str,
        voice_override: Optional[str],
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Maps tool outputs to visual and sources conforming to Answer Contract schema.

        Handles multi-tool turns (e.g. policy search + data query for P11-style questions).
        """
        if not tool_responses:
            return {"type": "none", "mode": visual_mode}, [{"kind": "data", "object": "ONGC Enterprise Data Bank"}]

        sources = []
        clause_obj = None
        data_visual = None

        certified_resp = next((r for r in tool_responses if r["name"] == "run_certified_query"), None)
        query_resp = next((r for r in tool_responses if r["name"] == "query_data"), None)
        policy_resp = next((r for r in tool_responses if r["name"] == "search_policy"), None)
        whatif_resp = next((r for r in tool_responses if r["name"] == "what_if"), None)
        draft_resp = next((r for r in tool_responses if r["name"] == "draft_document"), None)

        # 1. Process Certified Query Result
        if certified_resp:
            resp = certified_resp["response"]
            sql = resp.get("executed_sql", "")
            rows = resp.get("rows", [])
            columns = resp.get("columns", [])
            prov = resp.get("provenance", {})
            gold_objs = prov.get("gold_objects", "hrfin_gold")
            sources.append({
                "kind": "data",
                "object": gold_objs,
                "sql": sql,
            })
            clean_title, subtitle = make_clean_title_and_subtitle(
                query=query,
                entry_id=resp.get("query_id"),
                params=resp.get("params_applied"),
            )
            vis_meta = resp.get("visual", {})
            vis_type = vis_meta.get("type", "table")
            if vis_type == "refusal":
                data_visual = {
                    "type": "refusal",
                    "mode": visual_mode,
                    "title": clean_title,
                    "subtitle": subtitle,
                    "table": {"columns": columns, "rows": rows[:20]},
                }
            elif vis_type == "document":
                data_visual = {
                    "type": "document",
                    "mode": visual_mode,
                    "title": clean_title,
                    "subtitle": subtitle,
                    "document": {"title": clean_title, "content": resp.get("deterministic_summary", "")},
                }
            elif (vis_type not in ("refusal", "document", "clause") or voice_override) and len(rows) > 1 and len(columns) >= 2:
                ck = voice_override or ("line" if vis_type == "line_chart" else "grouped_bar" if vis_type == "grouped_bar" else "waterfall" if vis_type == "waterfall_chart" else "hbar")
                if ck == "table":
                    data_visual = {
                        "type": "table",
                        "mode": visual_mode,
                        "title": clean_title,
                        "subtitle": subtitle,
                        "table": {"columns": columns, "rows": rows[:25]},
                    }
                else:
                    chart_spec = build_chart_spec(kind=ck, columns=columns, rows=rows, title=clean_title)
                    data_visual = {
                        "type": "chart",
                        "mode": visual_mode,
                        "title": clean_title,
                        "subtitle": subtitle,
                        "chart": chart_spec,
                        "table": {"columns": columns, "rows": rows[:25]},
                    }
            else:
                data_visual = {
                    "type": "table",
                    "mode": visual_mode,
                    "title": clean_title,
                    "subtitle": subtitle,
                    "table": {"columns": columns, "rows": rows[:20]},
                }

        # 2. Process Policy Result
        if policy_resp:
            resp = policy_resp["response"]
            clauses = resp.get("clauses", [])
            c0 = clauses[0] if clauses else {}
            doc_id = c0.get("doc_id", "JRTP")
            clause_ref = c0.get("clause_ref", "Clause 3.0")
            text = c0.get("text", "Official policy norms.")
            sources.append({
                "kind": "policy",
                "doc_id": doc_id,
                "clause": clause_ref,
                "title": c0.get("doc_title", doc_id),
            })
            clause_obj = {
                "doc_id": doc_id,
                "doc_title": c0.get("doc_title", doc_id),
                "clause_ref": clause_ref,
                "text": text,
                "highlight": text[:250],
                "provenance": c0.get("provenance", "illustrative"),  # P0.7 (BUG-31)
            }

        # 2. Process Data Result
        if query_resp:
            resp = query_resp["response"]
            sql = ""
            for tc in tool_calls:
                if tc["name"] == "query_data":
                    sql = tc["args"].get("sql_query", "")
                    break
            rows = resp.get("all_rows") or resp.get("rows", [])
            columns = resp.get("columns", [])
            sources.append({
                "kind": "data",
                "object": "hrfin_gold",
                "sql": sql,
            })

            chart_kind = select_chart_kind(columns=columns, rows=rows, question_type="data", voice_override=voice_override)
            clean_title = make_clean_title(query)
            if chart_kind == "table" or not rows:
                data_visual = {
                    "type": "table",
                    "mode": visual_mode,
                    "title": clean_title,
                    "table": {
                        "columns": columns,
                        "rows": rows[:20],
                    },
                }
            else:
                chart_spec = build_chart_spec(kind=chart_kind, columns=columns, rows=rows, title=clean_title)
                data_visual = {
                    "type": "chart",
                    "mode": visual_mode,
                    "title": clean_title,
                    "chart": chart_spec,
                    "table": {
                        "columns": columns,
                        "rows": rows[:20],
                    },
                }

        # 3. Process What-If Result
        if whatif_resp:
            resp = whatif_resp["response"]
            sql = resp.get("sql", "")
            rows = resp.get("rows", [])
            columns = resp.get("columns", [])
            scen = resp.get("scenario", "what_if")
            sources.append({
                "kind": "data",
                "object": "hrfin_gold.v_field_pnl",
                "sql": sql,
            })
            chart_spec = build_chart_spec(kind="waterfall", columns=columns, rows=rows, title=f"Scenario Simulation: {scen}")
            data_visual = {
                "type": "chart",
                "mode": visual_mode,
                "title": f"Scenario Simulation: {scen}",
                "chart": chart_spec,
                "table": {
                    "columns": columns,
                    "rows": rows[:20],
                },
            }

        # 4. Process Document Draft Result
        if draft_resp:
            resp = draft_resp["response"]
            doc_type = resp.get("doc_type", "board_note")
            title = resp.get("title", "Official ONGC Document Draft")
            markdown = resp.get("markdown", "")
            version = resp.get("version", 1)
            sources.append({
                "kind": "document",
                "title": resp.get("template_id", "ONGC Secretariat Template"),
            })
            return {
                "type": "document",
                "mode": visual_mode,
                "title": title,
                "document": {
                    "doc_type": doc_type,
                    "title": title,
                    "markdown": markdown,
                    "template_id": resp.get("template_id", "template_board_note.docx"),
                    "version": version,
                },
            }, sources

        # Multi-Tool Resolution (Policy + Data)
        if data_visual and clause_obj:
            # Attach clause card to chart/table visual
            data_visual["clause"] = clause_obj
            return data_visual, sources
        elif data_visual:
            return data_visual, sources
        elif clause_obj:
            return {
                "type": "clause",
                "mode": visual_mode,
                "title": f"{clause_obj['doc_id']} {clause_obj['clause_ref']}",
                "clause": clause_obj,
            }, sources

        return {"type": "none", "mode": visual_mode}, [{"kind": "data", "object": "ONGC Data Bank"}]


# Global Turn Runner Singleton
_GLOBAL_RUNNERS: dict[str, AgentTurnRunner] = {}



def get_agent_turn_runner(model_name: Optional[str] = None, principal: Optional[Any] = None) -> AgentTurnRunner:
    global _GLOBAL_RUNNERS
    from app.auth import get_active_principal
    p = principal or get_active_principal()
    key = p.persona if p else "junior"
    if model_name:
        key = f"{key}_{model_name}"
    
    if key not in _GLOBAL_RUNNERS:
        _GLOBAL_RUNNERS[key] = AgentTurnRunner(model_name=model_name, principal=p)
    return _GLOBAL_RUNNERS[key]
