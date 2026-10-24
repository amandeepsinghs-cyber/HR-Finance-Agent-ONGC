import pytest
import os
import asyncio
from app.turn_runner import AgentTurnRunner

def test_no_in_q_clean_in_turn_runner():
    path = os.path.join(os.path.dirname(__file__), "../app/turn_runner.py")
    with open(path, "r") as f:
        content = f.read()
    assert "in q_clean" not in content, "grep -c 'in q_clean' turn_runner.py is not 0"

def test_no_hardcoded_numbers():
    path = os.path.join(os.path.dirname(__file__), "../app/turn_runner.py")
    with open(path, "r") as f:
        content = f.read()
    for literal in ["33108.97", "84.0", "42.6", "29.1", "Champang", "Borholla"]:
        assert literal not in content, f"Hardcoded literal {literal} found in turn_runner.py"

def test_no_asset_economics_turn():
    path = os.path.join(os.path.dirname(__file__), "../app/turn_runner.py")
    with open(path, "r") as f:
        content = f.read()
    assert "_maybe_asset_economics_comparison_turn" not in content, "Found _maybe_asset_economics_comparison_turn"

@pytest.mark.asyncio
async def test_ui_control_intent():
    runner = AgentTurnRunner()
    # Mock some methods if needed or rely on the deterministic logic
    contract = await runner.execute_turn_async(
        query="show as a table",
        session_id="test_session_1",
        persona="CMD"
    )
    assert contract["visual"]["type"] == "none"

@pytest.mark.asyncio
async def test_greeting_intent():
    runner = AgentTurnRunner()
    contract = await runner.execute_turn_async(
        query="who are you",
        session_id="test_session_1",
        persona="CMD"
    )
    assert "I am Yukti" in contract.get("spoken_summary", "")

@pytest.mark.asyncio
async def test_policy_intent():
    runner = AgentTurnRunner()
    contract = await runner.execute_turn_async(
        query="what is the leave policy",
        session_id="test_session_1",
        persona="CMD"
    )
    # The return depends on PolicySearchEngine, if it works without mocks
    assert contract is not None

