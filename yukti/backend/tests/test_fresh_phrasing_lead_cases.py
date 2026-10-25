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
    assert "Details screen par hain" in spoken, f"Missing Hinglish closing line: {spoken}"

    # 3. Templated title & human-only subtitle
    assert ("Dehradun" in title or "Dehradun" in subtitle) and ("≥5" in title or ">= 5" in title)
    assert "Dehradun" in subtitle or "Headcount" in subtitle
    assert "WC-" not in subtitle, f"Found raw technical work centre codes in subtitle: {subtitle}"


@pytest.mark.asyncio
async def test_cmd_lost_money_gets_answer_e2_gets_refusal_no_cache_poisoning():
    runner = get_agent_turn_runner(model_name="gemini-2.5-flash")
    ac = get_answer_cache()
    ac.clear()

    q = "Which fields lost money last year?"

    import csv
    from pathlib import Path

    copa_v3 = Path(__file__).resolve().parents[3] / "data_bank" / "landing" / "sap" / "CO_PA_v3.csv"
    expected_mn = {}
    with copa_v3.open("r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("fy") == "FY26" and r.get("line_code") == "PL.PBT":
                oid = r["object_id"]
                expected_mn[oid] = expected_mn.get(oid, 0.0) + float(r["amount_inr_mn"])
    expected_pbt = {oid: round(val / 10.0, 2) for oid, val in expected_mn.items()}
    bar_str = f"{abs(expected_pbt['FLD-BAR']):.2f}"
    pas_str = f"{abs(expected_pbt['FLD-PAS']):.2f}"

    # 1. CMD must get allowed P&L answer
    res_cmd = await runner.execute_turn_async(q, session_id="test-lost-money-cmd-suite", persona="CMD")
    assert res_cmd.get("access", {}).get("status") == "allowed"
    assert res_cmd.get("visual", {}).get("type") in ("table", "chart")
    spoken_cmd = res_cmd.get("spoken_summary", "")
    assert ("Baramura" in spoken_cmd and bar_str in spoken_cmd) or ("Pasarlapudi" in spoken_cmd and pas_str in spoken_cmd)
    rows_cmd = {r["field"]: r["pbt_cr"] for r in res_cmd["visual"]["table"]["rows"]}
    assert rows_cmd.get("Pasarlapudi") == expected_pbt["FLD-PAS"] and rows_cmd.get("Baramura") == expected_pbt["FLD-BAR"]
    assert "WC-" not in res_cmd.get("visual", {}).get("subtitle", "")

    # 2. E2 must get refusal
    res_e2 = await runner.execute_turn_async(q, session_id="test-lost-money-e2-suite", persona="E2_HR")
    assert res_e2.get("visual", {}).get("type") == "refusal"

    # 3. CMD re-query must still get allowed answer (no cache poisoning from E2)
    res_cmd2 = await runner.execute_turn_async(q, session_id="test-lost-money-cmd2-suite", persona="CMD")
    assert res_cmd2.get("access", {}).get("status") == "allowed"
    assert res_cmd2.get("visual", {}).get("type") in ("table", "chart")
    spoken_cmd2 = res_cmd2.get("spoken_summary", "")
    assert ("Baramura" in spoken_cmd2 and bar_str in spoken_cmd2) or ("Pasarlapudi" in spoken_cmd2 and pas_str in spoken_cmd2)
    rows_cmd2 = {r["field"]: r["pbt_cr"] for r in res_cmd2["visual"]["table"]["rows"]}
    assert rows_cmd2.get("Pasarlapudi") == expected_pbt["FLD-PAS"] and rows_cmd2.get("Baramura") == expected_pbt["FLD-BAR"]
