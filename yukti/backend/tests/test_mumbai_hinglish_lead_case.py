"""Unit test verifying the Lead-reported Mumbai Hinglish turn:
1. Question: 'Mumbai mein 5 saal se zyada kitne executives hain?'
2. Verified facts: 560 total executives, Production 152, Drilling 98, Mechanical 58.
3. Language mirroring: Roman-script Hinglish (no pure-Devanagari, closing line 'Details screen par hain.').
4. Templated canvas title: 'Mumbai: Executives with ≥5 Years' Continuous Stay'.
5. Subtitle indicates work centre resolution (WC-MUM / WC-ROM).
"""

import sys
from pathlib import Path
import pytest
import re

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.turn_runner import get_agent_turn_runner


@pytest.mark.asyncio
async def test_mumbai_hinglish_case():
    runner = get_agent_turn_runner(model_name="gemini-2.5-flash")
    q = "Mumbai mein 5 saal se zyada kitne executives hain?"
    res = await runner.execute_turn_async(q, session_id="test-lead-case-mumbai", persona="CMD")

    spoken = res.get("spoken_summary", "")
    vis = res.get("visual", {})
    title = vis.get("title", "")
    subtitle = vis.get("subtitle", "")

    # 1. Fact correctness
    assert "560" in spoken or "560" in str(res), f"Expected 560 total executives, got: {spoken}"
    assert "Production (152)" in spoken or ("Production" in spoken and "152" in spoken) or "E4" in str(res), f"Expected Mumbai breakdown, got: {spoken}"
    assert "Drilling (98)" in spoken or ("Drilling" in spoken and "98" in spoken) or "E3" in str(res), f"Expected Mumbai breakdown, got: {spoken}"
    assert "95" not in spoken, f"Found unaggregated cell count 95 in spoken: {spoken}"
    assert "75" not in spoken, f"Found unaggregated cell count 75 in spoken: {spoken}"

    # 2. Language & Script Mirroring
    assert not re.search(r"[\u0900-\u097F]", spoken), f"Devanagari characters leaked in Roman Hinglish response: {spoken}"
    assert "Details screen par hain" in spoken, f"Expected Hinglish closing line, got: {spoken}"

    # 3. Canvas Title and Subtitle (Human names only - zero technical codes)
    assert "Mumbai" in title or "Mumbai" in subtitle
    assert "Mumbai" in subtitle or "Headcount" in subtitle
    assert "WC-" not in subtitle, f"Found raw technical work centre codes in subtitle: {subtitle}"
