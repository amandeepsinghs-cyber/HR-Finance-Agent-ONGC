"""Unit tests for Lead-reported fresh phrasing cases:
1. 'Dehradun mein 5 saal se zyada kitne officers posted hain?' resolves to Dehradun Tel Bhavan
   and returns 455 executives with Roman-script Hinglish and human-only subtitle.
2. 'Which fields lost money last year?' gives CMD an allowed P&L table (Champang -4.93 Cr)
   and E2 a refusal, with strict persona cache isolation and zero cache poisoning.
"""

import sys
from pathlib import Path
import pytest
import re

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.answer_cache import get_answer_cache
from app.turn_runner import get_agent_turn_runner


@pytest.mark.asyncio
async def test_dehradun_officers_hinglish_resolves_and_returns_facts():
    runner = get_agent_turn_runner(model_name="gemini-2.5-flash")
    q = "Dehradun mein 5 saal se zyada kitne officers posted hain?"
    res = await runner.execute_turn_async(q, session_id="test-ddn-lead-suite", persona="CMD")

    spoken = res.get("spoken_summary", "")
    vis = res.get("visual", {})
    title = vis.get("title", "")
    subtitle = vis.get("subtitle", "")

    # 1. Fact correctness (Dehradun Tel Bhavan continuous stay >=60m = 455 executives)
    assert "455" in spoken or "455" in str(res), f"Expected 455 executives in Dehradun, got: {spoken}"
    assert "A total of 0" not in spoken, f"Spoke 0 executives for Dehradun: {spoken}"

    # 2. Language & Script Mirroring
    assert not re.search(r"[\u0900-\u097F]", spoken), f"Devanagari leaked in Roman Hinglish: {spoken}"
    assert "Details screen par hain" in spoken, f"Missing Hinglish closing phrase: {spoken}"

    # 3. Templated title & human-only subtitle
    assert "Dehradun: Executives with ≥5 Years' Continuous Stay" in title
    assert "Dehradun Tel Bhavan Corporate Administration" in subtitle
    assert "WC-" not in subtitle, f"Found raw technical work centre codes in subtitle: {subtitle}"


@pytest.mark.asyncio
async def test_cmd_lost_money_gets_answer_e2_gets_refusal_no_cache_poisoning():
    runner = get_agent_turn_runner(model_name="gemini-2.5-flash")
    ac = get_answer_cache()
    ac.clear()

    q = "Which fields lost money last year?"

    # 1. CMD must get allowed P&L answer
    res_cmd = await runner.execute_turn_async(q, session_id="test-lost-money-cmd-suite", persona="CMD")
    assert res_cmd.get("access", {}).get("status") == "allowed"
    assert res_cmd.get("visual", {}).get("type") in ("table", "chart")
    assert "Champang" in res_cmd.get("spoken_summary", "")
    assert "4.93" in res_cmd.get("spoken_summary", "")
    assert "WC-" not in res_cmd.get("visual", {}).get("subtitle", "")

    # 2. E2 must get refusal
    res_e2 = await runner.execute_turn_async(q, session_id="test-lost-money-e2-suite", persona="E2_HR")
    assert res_e2.get("visual", {}).get("type") == "refusal"

    # 3. CMD re-query must still get allowed answer (no cache poisoning from E2)
    res_cmd2 = await runner.execute_turn_async(q, session_id="test-lost-money-cmd2-suite", persona="CMD")
    assert res_cmd2.get("access", {}).get("status") == "allowed"
    assert res_cmd2.get("visual", {}).get("type") in ("table", "chart")
    assert "Champang" in res_cmd2.get("spoken_summary", "")
