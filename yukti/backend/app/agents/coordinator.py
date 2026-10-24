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

    # 2. Standard router
    router = get_router()
    agent_id = router.route(query)
    
    registry = get_registry()
    agent_info = registry.get_agent(agent_id)
    
    if not agent_info:
        # Fallback to analyst
        agent_id = "analyst"
        agent_info = registry.get_agent(agent_id)
        
    # 3. RBAC Enforcement
    if agent_info.requires_role:
        if persona not in agent_info.requires_role:
            return {
                "answer": "I am sorry, but your role is not authorized to execute this agent.",
                "access": {"status": "refused"},
                "rule_ref": f"RBAC-AGENT-{agent_id.upper().replace('_AGENT', '')}",
                "alternative": "I can show the WACC series and the published valuation ratios instead",
                "ui_action": None
            }
        else:
            import uuid
            action_id = str(uuid.uuid4())
            pa = {
                "id": action_id,
                "agent": agent_id,
                "editable_inputs": {}
            }
            if session:
                if not hasattr(session, "pending_actions"):
                    session.pending_actions = {}
                session.pending_actions[action_id] = pa
            
            return {
                "proposed_action": pa,
                "answer": f"I can run the {agent_info.description}. Do you want to proceed?"
            }
            
    # For agents without role requirement, return intent
    return {"delegate_to": agent_id}
