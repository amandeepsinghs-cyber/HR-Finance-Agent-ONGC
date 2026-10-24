import pytest
import asyncio
from app.agents.types import AgentContext
from app.agents.doc_export import tool

@pytest.mark.asyncio
async def test_doc_export_fast():
    ctx = AgentContext(persona="CMD", session=None, turn_id="t1", language="en")
    res = await tool.run(ctx, {"est_seconds": 5})
    assert "artifacts" in res
    assert res["access"]["status"] == "allowed"

@pytest.mark.asyncio
async def test_doc_export_slow():
    ctx = AgentContext(persona="CMD", session=None, turn_id="t1", language="en")
    res = await tool.run(ctx, {"est_seconds": 15})
    assert "job" in res
    assert res["job"]["agent"] == "doc_export_agent"
    assert res["job"]["status"] == "pending"
