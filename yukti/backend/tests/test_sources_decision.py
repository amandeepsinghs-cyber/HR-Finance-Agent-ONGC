"""Unit test verifying the User Decision on Sources:
1. Normal turns NEVER mention sources, table names (hrfin_), or clause numbers in spoken_summary.
2. A follow-up asking "what's the source?" / "where is this from?" speaks the plain business source of the previous turn.
"""

import asyncio
from pathlib import Path
import re
import sys
import pytest

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.turn_runner import AgentTurnRunner


@pytest.mark.asyncio
async def test_no_sources_or_clause_numbers_in_spoken_summary_normal_turn():
    runner = AgentTurnRunner(model_name="gemini-2.5-flash")

    # Run C1 normal turn
    res = await runner.execute_turn_async(
        "How many executives have been posted in the Delhi office for 5 years or more? Break down by grade and discipline.",
        session_id="test-spoken-norm-1",
        persona="CMD",
    )
    spoken = res.get("spoken_summary", "")

    # Assert no table names (hrfin_)
    assert "hrfin_" not in spoken, f"Found table/dataset token in spoken summary: {spoken}"
    # Assert no raw clause numbers like 'Clause 3.0' or 'Clause 7'
    assert not re.search(r"\bClause\s+\d+", spoken, flags=re.IGNORECASE), f"Found clause number in spoken summary: {spoken}"
    # Assert no robotic boilerplate
    assert "interactive visual on your canvas" not in spoken.lower(), f"Found canvas boilerplate in spoken summary: {spoken}"


@pytest.mark.asyncio
async def test_whats_the_source_followup():
    runner = AgentTurnRunner(model_name="gemini-2.5-flash")
    session_id = "test-source-inquiry-session"

    # Turn 1: Ask an executive tenure question
    await runner.execute_turn_async(
        "How many executives have been posted in the Delhi office for 5 years or more?",
        session_id=session_id,
        persona="CMD",
    )

    # Turn 2: Follow-up asking for the source
    res_source = await runner.execute_turn_async(
        "Where is this from? What's the source?",
        session_id=session_id,
        persona="CMD",
    )
    spoken = res_source.get("spoken_summary", "")

    # Must speak the source in plain business language
    assert "comes from" in spoken.lower() or "posting records" in spoken.lower() or "data bank" in spoken.lower(), (
        f"Expected spoken source attribution, got: {spoken}"
    )
    # Must NOT speak raw database table or dataset names
    assert "hrfin_" not in spoken, f"Found raw database token in spoken source: {spoken}"
