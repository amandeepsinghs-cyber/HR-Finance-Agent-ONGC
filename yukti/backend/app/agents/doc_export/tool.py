import uuid
from typing import Dict, Any
from app.agents.types import AgentContext, AgentResult
from app.brain.rbac import enforce_contract

async def run(ctx: AgentContext, inputs: dict) -> AgentResult:
    est_s = inputs.get("est_seconds", 5)
    if est_s > 8:
        return {
            "turn_id": f"job:{uuid.uuid4().hex}",
            "job": {
                "id": f"job_{uuid.uuid4().hex}",
                "status": "pending",
                "agent": "doc_export_agent"
            }
        }
    
    contract = {
        "artifacts": [{"export_id": "exp_456", "kind": "xlsx"}],
        "access": {"status": "allowed"}
    }
    return enforce_contract(contract, ctx.persona)
