import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.agents.router import get_router
from app.agents.registry import get_registry
from app.intents.confirm import resolve_pending_proposal_async

logger = logging.getLogger(__name__)

async def route_turn(query: str, persona: str, session: Any = None) -> Dict[str, Any]:
    logger.info("route=coordinator")
    
    # 1. Resolve pending proposals (confirm/cancel/edit)
    if session and hasattr(session, "pending_actions") and session.pending_actions:
        resolved = await resolve_pending_proposal_async(query, session)
        if resolved:
            return resolved

    from app.intents.confirm import extract_voice_edits
    edits = extract_voice_edits(query)
    if edits and session and hasattr(session, "last_agent_result") and getattr(session, "last_agent_result"):
        last = session.last_agent_result
        if last.get("agent") == "dcf_agent":
            import uuid
            action_id = str(uuid.uuid4())
            pa = {
                "id": action_id,
                "agent": "dcf_agent",
                "editable_inputs": [{"key": k, "value": v, "edited_by_user": True} for k, v in edits.items()],
                "inputs": edits
            }
            if not hasattr(session, "pending_actions"):
                session.pending_actions = {}
            session.pending_actions[action_id] = pa
            return {
                "proposed_action": pa,
                "answer": "Updated assumptions. Do you want to proceed?"
            }

    # 2. Fast regex router first (avoids 40 synchronous embedding calls on normal analyst turns)
    registry = get_registry()
    agent_id: Optional[str] = None
    import re
    for agent in registry.agents:
        for trig in agent.triggers:
            if re.search(trig, query or "", re.IGNORECASE):
                agent_id = agent.id
                break
        if agent_id:
            break
    if re.search(r"मूल्यांकन", query or ""):
        agent_id = "dcf_agent"
    if not agent_id:
        agent_id = "analyst"

    agent_info = registry.get_agent(agent_id)
    if not agent_info:
        agent_id = "analyst"
        agent_info = registry.get_agent(agent_id)

    # 3. RBAC Enforcement & Confirmation Gate (SPEC-03: only dcf_agent is confirmation-gated)
    if agent_info and agent_info.requires_role and persona not in agent_info.requires_role:
        return {
            "answer": "I am sorry, but your role is not authorized to execute this agent.",
            "access": {"status": "refused"},
            "rule_ref": f"RBAC-AGENT-{agent_id.upper().replace('_AGENT', '')}",
            "alternative": "I can show the WACC series and the published valuation ratios instead",
            "ui_action": None,
        }

    if agent_id == "dcf_agent":
        from app.agents.dcf_contract import build_dcf_proposal
        prop = build_dcf_proposal(persona, session)
        pa = prop.get("proposed_action")
        if pa and session is not None:
            if not hasattr(session, "pending_actions"):
                session.pending_actions = {}
            session.pending_actions[pa["id"]] = pa
        return prop

    # 4. SPEC-03 / SPEC-11 §2 row 10: Board notes & document drafting route through doc_export / email_agent after RBAC
    q_low = (query or "").lower()
    is_doc_draft = bool(
        re.search(
            r"^\s*(?:please\s+)?(?:draft|prepare|write|generate|create|compose)\b.*\b(?:board\s+note|agenda\s+note|briefing(?:\s+note)?|parliament(?:\s+reply)?|memo|memorandum|note|reply|document)\b",
            query or "",
            re.I,
        )
        and not re.search(r"\b(?:transfer\s+note|email|letter|excel|xlsx|csv)\b", q_low)
    )
    if is_doc_draft:
        from app.brain.rbac import decide
        from app.answer_composer import build_refusal_contract
        from app.tools.draft_document import DocumentDraftingEngine
        import asyncio
        import time

        data_cls = ["board_confidential"] if "board" in q_low else ["general_fin"]
        pol = decide(persona, data_cls, query)
        if pol.action == "refuse":
            ref_c = build_refusal_contract(
                code=pol.code or "R-BOARD",
                persona=persona,
                turn_id=f"turn-doc-refusal-{int(time.time())}",
                language="en",
                rule_ref=pol.rule_ref,
                latency_ms=1.0,
            )
            return {"contract": ref_c}

        last_turn = session.turns[-1] if (session and getattr(session, "turns", None)) else {}
        last_vis = (last_turn.get("visual") or {}) if isinstance(last_turn, dict) else {}
        ctx_rows = (getattr(session, "last_rows", None) if session else None) or (last_vis.get("table") or {}).get("rows") or []
        ctx_cols = (getattr(session, "last_columns", None) if session else None) or (last_vis.get("table") or {}).get("columns") or []
        ctx_title = last_vis.get("title") or ""
        ctx_summary = last_turn.get("spoken_summary") if isinstance(last_turn, dict) else ""
        doc_type_req = "parliament_reply" if any(w in q_low for w in ("parliament", "rajya sabha", "lok sabha")) else "board_note"
        doc_res = await asyncio.to_thread(
            DocumentDraftingEngine().draft,
            doc_type=doc_type_req,
            query=query,
            version=1,
            context_data={
                "rows": ctx_rows,
                "columns": ctx_cols,
                "title": ctx_title,
                "summary_text": ctx_summary,
            },
        )
        doc_title = doc_res.get("title", "Executive Briefing Note")
        spoken_doc = (
            f"I have drafted the official document '{doc_title}' grounded in ONGC's Single Source of Truth data. "
            f"You can review the full formatted memorandum on screen and export it directly to Word, PDF, or Excel."
        )
        doc_vis: Dict[str, Any] = {
            "type": "document",
            "mode": "replace",
            "title": doc_title,
            "subtitle": "Drafted from SSOT · Ready for .docx, .pdf & .xlsx Export",
            "document": {
                "doc_type": doc_res.get("doc_type", "board_note"),
                "title": doc_title,
                "markdown": doc_res.get("markdown", ""),
                "template_id": doc_res.get("template_id", "template_board_note.docx"),
                "version": 1,
            },
        }
        if ctx_rows and ctx_cols:
            doc_vis["table"] = {"columns": ctx_cols, "rows": ctx_rows[:25]}
        doc_contract = {
            "turn_id": f"turn-doc-{int(time.time())}",
            "language": getattr(session, "language", "en") if session else "en",
            "persona": persona,
            "spoken_summary": spoken_doc,
            "display_text": spoken_doc,
            "visual": doc_vis,
            "insights": [
                f"Official draft prepared: {doc_title}",
                "1-click export enabled for Word (.docx), PDF (.pdf), and Excel (.xlsx)",
            ],
            "sources": [{"kind": "document", "title": doc_res.get("template_id", "template_board_note.docx")}],
            "suggestions": [
                "Make it shorter and more concise",
                "Translate this note to Hindi",
                "Show the underlying data as a bar chart",
            ],
            "access": {"status": "allowed"},
            "export_options": ["word", "pdf", "xlsx", "docs"],
            "status_events": [f"Drafted official document via doc_export_agent: {doc_title}"],
        }
        return {"contract": doc_contract}

    # For non-confirmation-gated agents, delegate to the One-Brain planner pipeline
    return {"delegate_to": agent_id}
