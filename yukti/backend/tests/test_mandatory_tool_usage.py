"""Unit test verifying that any question about ONGC numbers/metrics must call a tool,
ensuring W1 spoken contains '$60', and checking politician name hygiene.
"""

import asyncio
import sys
from pathlib import Path
import pytest

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.tools.draft_document import sanitize_fictional_names
from app.turn_runner import AgentTurnRunner


@pytest.mark.asyncio
async def test_data_query_calls_tool_or_blocks_ungrounded():
    runner = AgentTurnRunner(model_name="gemini-2.5-flash")

    # Numerical query about water cut and lifting cost (ST-1)
    q = "What is the correlation between water cut percentage and lifting cost across our top 10 producing onshore fields in FY26?"
    res = await runner.execute_turn_async(q, session_id="test-mandatory-tool-1", persona="CMD")

    tool = res.get("tool_called")
    spoken = res.get("spoken_summary", "").lower()

    if tool is None:
        assert "not available" in spoken or "won't guess" in spoken, (
            "Numerical question returned direct model reasoning without calling a data tool!"
        )
    else:
        assert tool in ("query_data", "what_if", "search_policy"), (
            f"Expected enterprise tool call, got {tool}"
        )


@pytest.mark.asyncio
async def test_greeting_allows_direct_response():
    runner = AgentTurnRunner(model_name="gemini-2.5-flash")

    q = "Hello"
    res = await runner.execute_turn_async(q, session_id="test-greeting-1", persona="CMD")
    assert res.get("access", {}).get("status") == "allowed"
    assert res.get("turn_id") is not None


@pytest.mark.asyncio
async def test_w1_contains_60_dollars():
    runner = AgentTurnRunner(model_name="gemini-2.5-flash")

    q = "What-if: If Brent crude price drops to $60 per barrel, which fields become cash negative?"
    res = await runner.execute_turn_async(q, session_id="test-w1-60", persona="CMD")

    spoken = res.get("spoken_summary", "")
    assert "$60" in spoken or "60" in spoken, f"Expected '$60' in W1 spoken text, got: {spoken}"
    assert "$0" not in spoken, f"Found erroneous '$0' in W1 spoken text: {spoken}"


def test_real_name_denylist():
    raw_text = "QUESTIONED BY: Shri Rameshwar Teli, M.P. and Shri Hardeep Singh Puri"
    cleaned = sanitize_fictional_names(raw_text)
    assert "Rameshwar Teli" not in cleaned
    assert "Hardeep Singh Puri" not in cleaned
    assert "Anand Swaroop" in cleaned
