
import pytest
import asyncio
import time
from app.brain.compiler import get_compiler
from app.brain.query_spec import QuerySpec, Period
from app.brain.pipeline import run_planner_turn
from app.session_memory import get_session_manager
import app.config

def test_p110a_b2_sql():
    c = get_compiler()
    spec = QuerySpec(version=1, domain="finance", metric="balance_sheet", period=Period(fy="FY24"), grain="aggregate")
    compiled = c.compile(spec)
    assert "source_table = 'standalone_balance_sheet'" in compiled.sql
    assert "is_own_vintage = TRUE" in compiled.sql
    assert "report_vintage = 'AR_FY2023-24'" in compiled.sql

@pytest.mark.asyncio
async def test_p110a_end_to_end():
    sm = get_session_manager()
    sess = sm.get_or_create(f"p110a-test-{time.time_ns()}", persona="hr_manager", language="en")
    
    app.config.YUKTI_FIN_SSOT_V3 = True
    
    questions = [
        "Balance sheet for 2024",
        "What is the 5-year trend for P&L?",
        "Show me the PAT trend",
        "What is the ROCE?",
        "Cash flow statement for FY24"
    ]
    
    for q in questions:
        res = await run_planner_turn(q, sess, "hr_manager", "turn1", "en", time.time())
        assert res is not None
        if q == "Balance sheet for 2024":
            table = res.get("contract", {}).get("visual", {}).get("table")
            if not table:
                print(res)
            assert table is not None
            cols = table["columns"]
            assert any("prior_fy_cr" in k for k in cols)
            # R2-B3: Face rows only for the FY24 BS (47)
            assert len(table["rows"]) == 47, f"Expected 47 face rows, got {len(table['rows'])}"
            
def test_p110a_flag_off():
    app.config.YUKTI_FIN_SSOT_V3 = False
    c = get_compiler()
    spec = QuerySpec(version=1, domain="finance", metric="balance_sheet", period=Period(fy="FY24"), grain="aggregate")
    compiled = c.compile(spec)
    assert "source_table = 'standalone_balance_sheet'" not in compiled.sql
    app.config.YUKTI_FIN_SSOT_V3 = True
