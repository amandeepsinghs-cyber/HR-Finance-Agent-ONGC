import pytest
import asyncio
from app.agents.types import AgentContext
from app.agents.hr_transfer import tool

@pytest.mark.asyncio
async def test_hr_transfer_draft():
    ctx = AgentContext(persona="CMD", session=None, turn_id="t1", language="en")
    res = await tool.run(ctx, {"action": "draft"})
    assert res["visual"]["type"] == "email_draft"
    assert res["access"]["status"] == "allowed"
    assert "artifacts" in res

@pytest.mark.asyncio
async def test_hr_transfer_send():
    ctx = AgentContext(persona="CMD", session=None, turn_id="t1", language="en")
    res = await tool.run(ctx, {"action": "send"})
    assert "proposed_action" in res
    assert res["proposed_action"]["agent"] == "hr_transfer_agent"
    assert "email.send" in res["proposed_action"]["requires_permission"]
