import pytest
import time
import os
from app.brain.pipeline import run_planner_turn
from app.turn_runner import AgentTurnRunner
from app.brain.query_spec import QuerySpec
import app.config

# Mock session state since we might not be able to import session_manager properly
class MockSessionState:
    def __init__(self, turns=None, spec_history=None):
        self.turns = turns or []
        self.spec_history = spec_history or []
        self.last_rows = []

@pytest.fixture(autouse=True)
def setup_config(monkeypatch):
    monkeypatch.setenv("YUKTI_CLARIFY_TEST", "1")
    monkeypatch.setenv("YUKTI_FIN_SSOT_V3", "1")
    monkeypatch.setenv("YUKTI_PLANNER", "1")
    monkeypatch.setenv("YUKTI_FORCE_BQ_FAIL", "1")

@pytest.mark.asyncio
async def test_year_clarify_ac01():
    sess = MockSessionState()
    
    contract = await run_planner_turn("Can I see the income statement?", sess, "dir_fin", "turn1", "en", time.time())
    
    assert contract is not None
    assert "clarify" in contract["contract"]
    clarify = contract["contract"]["clarify"]
    assert clarify["slot"] == "fiscal_period"
    
    opts = clarify["options"]
    assert len(opts) == 4
    assert opts[0]["value"] == "FY26"
    assert opts[1]["value"] == "FY25"
    assert opts[2]["value"] == "FY22..FY26"
    assert opts[3]["value"] == "FY17..FY26"

@pytest.mark.asyncio
async def test_year_clarify_context_carryover():
    spec = QuerySpec(metric="balance_sheet", period={"fy": "FY24"})
    sess = MockSessionState(spec_history=[spec.to_contract()])
    
    contract = await run_planner_turn("show the income statement", sess, "dir_fin", "turn2", "en", time.time())
    
    if contract is not None:
        assert "clarify" not in contract.get("contract", {})
        # check that spoken_summary has context carryover text
        assert "Showing FY24, as before" in contract["contract"].get("spoken_summary", "")

PHRASES = [
    ("present year", "FY26"),
    ("this year", "FY26"),
    ("current", "FY26"),
    ("latest", "FY26"),
    ("is saal", "FY26"),
    ("last year", "FY25"),
    ("previous year", "FY25"),
    ("pichhle saal", "FY25"),
    ("2025", "FY25"),
    ("FY25", "FY25"),
    ("FY 2024-25", "FY25"),
    ("2024-25", "FY25"),
    ("five years", "FY22..FY26"),
    ("5 saal", "FY22..FY26"),
    ("last 5", "FY22..FY26"),
    ("5-year trend (FY22–FY26)", "FY22..FY26"),
    ("ten years", "FY17..FY26"),
    ("decade", "FY17..FY26"),
    ("10 saal", "FY17..FY26")
]

@pytest.mark.parametrize("query, expected_fy", PHRASES)
@pytest.mark.asyncio
async def test_year_clarify_resolution(query, expected_fy):
    runner = AgentTurnRunner(None)
    session_id = f"test_session_{query.replace(' ', '_')}"
    
    # Turn 1
    c1 = await runner.execute_turn_async(
        query="Can I see the income statement?",
        session_id=session_id,
        persona="dir_fin"
    )
    assert c1.get("clarify") is not None
    
    # Turn 2
    c2 = await runner.execute_turn_async(
        query=query,
        session_id=session_id,
        persona="dir_fin"
    )
    
    # Clarify should be resolved
    assert c2.get("clarify") is None
    
    # We should get a data response, meaning the pipeline executed.
    # The pipeline will put the resolved spec in the query_spec
    qs = c2.get("query_spec", {})
    period = qs.get("period", {})
    if ".." in expected_fy:
        expected_from, expected_to = expected_fy.split("..")
        assert period.get("from") == expected_from
        assert period.get("to") == expected_to
    else:
        assert period.get("fy") == expected_fy
        
    if query == "2025":
        assert "FY2024-25 (year ended 31-Mar-2025)" in c2.get("spoken_summary", "")

@pytest.mark.asyncio
async def test_year_clarify_expiry():
    runner = AgentTurnRunner(None)
    session_id = "test_session_expiry"
    
    # Turn 1
    c1 = await runner.execute_turn_async(
        query="Can I see the income statement?",
        session_id=session_id,
        persona="dir_fin"
    )
    assert c1.get("clarify") is not None
    
    # Turn 2 - Unrelated
    c2 = await runner.execute_turn_async(
        query="what is crude production?",
        session_id=session_id,
        persona="dir_fin"
    )
    # The clarify should expire, answering the new query.
    assert c2.get("clarify") is None
    qs = c2.get("query_spec", {})
    assert qs.get("metric") != "pnl_statement"
