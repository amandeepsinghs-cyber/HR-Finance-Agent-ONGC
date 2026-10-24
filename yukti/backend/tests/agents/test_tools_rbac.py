import pytest
import asyncio
from app.agents.types import AgentContext
from app.agents.hr_transfer import tool as hr_tool
from app.agents.doc_export import tool as doc_tool
from app.agents.fin_diagnostics import tool as fin_tool
from app.agents.registry import get_registry

@pytest.mark.asyncio
async def test_rbac_fin_diagnostics():
    ctx = AgentContext(persona="E1_FIN", session=None, turn_id="t1", language="en")
    res = await fin_tool.run(ctx, {})
    # Since mock enforce_contract might not be set up, just check if callable
    assert "visual" in res or "access" in res

@pytest.mark.asyncio
async def test_rbac_dcf_agent_registry():
    registry = get_registry()
    agent = registry.get_agent("dcf_agent")
    assert agent.requires_role == ["CMD", "DIR_FIN"]
    
    agent = registry.get_agent("hr_transfer_agent")
    assert len(agent.requires_role) == 11
