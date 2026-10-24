import pytest
import asyncio
from app.brain.pipeline import run_planner_turn
from app.brain.query_spec import QuerySpec, Period

class DummySession:
    def __init__(self):
        self.turns = []
        self.spec_history = []
        self.last_rows = []
        self.last_columns = []
        self.last_visual = None
        self.last_sql = ""
    def get_last_visual(self):
        return self.last_visual

@pytest.mark.asyncio
async def test_why_agent():
    session = DummySession()
    # Test AC-06: Why did revenue fall in FY23 (standalone)
    res = await run_planner_turn(
        "Why did revenue fall in FY23?",
        session,
        "CMD",
        "t1",
        "en",
        0.0
    )
    assert res is not None
    contract = res["contract"] if "contract" in res else res
    assert "visual" in contract
    assert "The numbers could not be fully grounded" not in contract["display_text"]

