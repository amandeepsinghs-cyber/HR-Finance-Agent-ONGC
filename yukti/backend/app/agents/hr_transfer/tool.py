import uuid
from typing import Dict, Any
from app.agents.types import AgentContext, AgentResult
from app.brain.rbac import enforce_contract

async def run(ctx: AgentContext, inputs: dict) -> AgentResult:
    action = inputs.get("action", "draft")
    
    if action == "send":
        return {
            "proposed_action": {
                "id": str(uuid.uuid4()),
                "agent": "hr_transfer_agent",
                "summary": "Send this email to Director (HR)?",
                "editable_inputs": {},
                "requires_permission": ["email.send"]
            },
            "answer": "Do you want to send this email?"
        }
        
    contract = {
        "visual": {
            "type": "email_draft",
            "mode": "replace",
            "email_draft": {
                "body_md": "As discussed...",
                "attachments": ["exp_123"]
            }
        },
        "artifacts": [{"export_id": "exp_123", "kind": "xlsx"}],
        "access": {"status": "allowed"}
    }
    return enforce_contract(contract, ctx.persona)
