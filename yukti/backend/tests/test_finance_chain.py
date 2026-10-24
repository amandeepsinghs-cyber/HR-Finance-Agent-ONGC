"""B4.5: finance flagship chain (V4) end to end as Director (Finance), YUKTI_PLANNER=1 (live).

most profitable / loss-making fields FY26 -> by capex invested -> under-invested vs reserves
-> vs MoU target -> draft board note. Every data answer must carry >= 2 grounded insights
and >= 2 drill-down chips, and the spoken answer must contain no ungrounded number.
"""

import asyncio
import os
from pathlib import Path
import re
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

QS = [
    "Which fields were the most profitable and which made losses in FY26?",
    "Show by capex invested over the last 5 years",
    "Which assets are under-invested relative to their reserves?",
    "How are we tracking against our MoU targets this year?",
    "Draft a board note on this",
]


@pytest.fixture(scope="module")
def chain():
    os.environ["YUKTI_PLANNER"] = "1"
    os.environ["YUKTI_RESULT_CACHE"] = "0"
    from app.turn_runner import AgentTurnRunner

    async def run():
        r = AgentTurnRunner(model_name="gemini-2.5-flash")
        sid = f"fin-flagship-{int(time.time())}"
        return [await r.execute_turn_async(q, session_id=sid, persona="DIR_FIN") for q in QS]

    try:
        return asyncio.run(run())
    finally:
        os.environ.pop("YUKTI_PLANNER", None)


def _grounded(c):
    from app.brain.narrator import grounding_violations
    nums = set()
    for r in (c["visual"].get("table") or {}).get("rows") or []:
        for v in r.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                nums.add(float(v))
    for i in c.get("insights_v2") or []:
        for t in re.findall(r"[−-]?\d[\d,]*(?:\.\d+)?", i["text"]):
            nums.add(float(t.replace(",", "").replace("−", "-")))
    nums |= {abs(x) for x in nums}
    return grounding_violations(c["spoken_summary"], nums)


@pytest.mark.parametrize("i", [0, 1, 2, 3])
def test_data_answers_have_insights_chips_and_grounding(chain, i):
    c = chain[i]
    assert c["persona"] == "DIR_FIN" and c["access"]["status"] == "allowed"
    assert c.get("query_spec"), c["spoken_summary"]
    assert len(c.get("insights_v2") or []) >= 2
    assert len(c.get("drilldowns") or []) >= 2
    assert _grounded(c) == []
    n = len([s for s in re.split(r"(?<=[.!?])\s+", c["spoken_summary"]) if s])
    print("SPOKEN:", c["spoken_summary"], "N:", n)
    assert 2 <= n <= 6


def test_t1_profit_and_loss_numbers(chain):
    rows = {r["field"]: r for r in chain[0]["visual"]["table"]["rows"]}
    assert rows["Mumbai High South"]["pbt_cr"] == 7753.84 and rows["Champang"]["pbt_cr"] == -183.27
    assert any(i["kind"] == "risk" and "Champang" in i["text"] for i in chain[0]["insights_v2"])


def test_t2_capex_by_asset(chain):
    c = chain[1]
    assert c["query_spec"]["metric"] == "capex_actual_cr"
    top = c["visual"]["table"]["rows"][0]
    assert top["asset"] == "Eastern Offshore" and round(top["capex_actual_cr"]) == 48955


def test_t3_under_investment_named(chain):
    c = chain[2]
    assert c["query_spec"]["metric"] == "capex_vs_reserves"
    assert any("under-invested" in i["text"] for i in c["insights_v2"])


def test_t4_mou_fy27(chain):
    c = chain[3]
    assert c["query_spec"]["metric"] == "mou_scorecard" and c["query_spec"]["period"]["fy"] == "FY27"
    assert len(c["visual"]["table"]["rows"]) == 9


def test_t5_board_note(chain):
    c = chain[4]
    assert c["visual"]["type"] == "document" and c["visual"]["document"]["markdown"]
