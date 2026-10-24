
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
    assert "report_vintage = 'AR_FY24'" in compiled.sql

@pytest.mark.asyncio
async def test_p110a_end_to_end(monkeypatch):
    monkeypatch.setenv("YUKTI_FORCE_BQ_FAIL", "1")
    sm = get_session_manager()
    sess = sm.get_or_create(f"p110a-test-{time.time_ns()}", persona="hr_manager", language="en")
    
    app.config.YUKTI_FIN_SSOT_V3 = True
    
    questions = [
        "Balance sheet for 2024",
        "What is the 5-year trend for P&L?",
        "Show me the PAT trend",
        "What is the ROCE for FY23?",
        "Cash flow statement for FY24"
    ]
    
    for q in questions:
        res = await run_planner_turn(q, sess, "hr_manager", "turn1", "en", time.time())
        assert res is not None
        if "trend" in q:
            insights = res.get("contract", {}).get("insights", [])
            for text in insights:
                text = text.lower()
                assert "of the total" not in text
                assert "hold" not in text and "top" not in text
        
        if q == "What is the ROCE for FY23?":
            table = res.get("contract", {}).get("visual", {}).get("table")
            assert table is not None
            assert len(table["rows"]) >= 1
        
        if q == "Balance sheet for 2024":
            table = res.get("contract", {}).get("visual", {}).get("table")
            if not table:
                print(res)
            assert table is not None
            cols = table["columns"]
            assert any("prior_fy_cr" in k for k in cols)
            # R2-B3: Face rows only for the FY24 BS (47)
            assert len(table["rows"]) == 47, f"Expected 47 face rows, got {len(table['rows'])}"
            # R3-B4: FY24 BS prior_fy_cr exactly matches AR FY24 printed comparative (FY23 = 369878.37)
            total_assets_row = next(r for r in table["rows"] if r["line_code"] == "BS.TOTAL_ASSETS")
            assert abs(total_assets_row["prior_fy_cr"] - 369878.37) < 0.1
            
def test_p110a_flag_off():
    app.config.YUKTI_FIN_SSOT_V3 = False
    c = get_compiler()
    spec = QuerySpec(version=1, domain="finance", metric="balance_sheet", period=Period(fy="FY24"), grain="aggregate")
    compiled = c.compile(spec)
    assert "source_table = 'standalone_balance_sheet'" not in compiled.sql
    app.config.YUKTI_FIN_SSOT_V3 = True
