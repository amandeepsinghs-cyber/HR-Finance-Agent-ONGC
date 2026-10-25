import pytest
import asyncio
from app.agents.dcf_contract import build_dcf_proposal
from app.agents.dcf_agent import dcf_job_runner

class MockSession:
    pass

def test_dcf_proposal():
    sess = MockSession()
    res = build_dcf_proposal("DIR_FIN", sess)
    assert "proposed_action" in res
    pa = res["proposed_action"]
    assert pa["agent"] == "dcf_agent"
    assert "CMD" in pa["requires_role"]
    assert "DIR_FIN" in pa["requires_role"]
    assert "wacc_pct" in pa["inputs"]
    assert abs(pa["inputs"]["wacc_pct"] - 11.6556) < 1e-4
    assert pa["lineage"]["wacc"]["source"] == "fact_wacc_annual FY26"
    assert abs(pa["lineage"]["market_price"]["close_inr"] - 284.65) < 1e-2

def test_dcf_proposal_stale():
    sess = MockSession()
    sess.market_stale = True
    res = build_dcf_proposal("DIR_FIN", sess)
    assert "Market price data is unavailable" in res["answer"]
    assert "run the model and show value per share only" in res["chips"]

def test_dcf_proposal_unverified():
    sess = MockSession()
    sess.ssot_unverified = True
    res = build_dcf_proposal("DIR_FIN", sess)
    assert res["proposed_action"] is None
    assert "hasn't passed verification yet" in res["answer"]
    assert res["access"]["status"] == "refused"

@pytest.mark.asyncio
async def test_dcf_job_runner():
    async def mock_emit(step, msg, prog):
        pass
    res = await dcf_job_runner("test_job_123", {"inputs": {"wacc_pct": 10.37}}, "sess_1", mock_emit)
    assert res["contract_version"] == 3
    assert res["turn_id"] == "job:test_job_123"
    assert res["visual"]["type"] == "dcf_model"
    assert "illustrative valuation" in res["spoken_summary"]

def test_dcf_proposal_what_if():
    sess = MockSession()
    res = build_dcf_proposal("CMD", sess, overrides={"wacc_pct": 11.0, "terminal_g_pct": 2.5})
    pa = res["proposed_action"]
    assert pa["inputs"]["wacc_pct"] == 11.0
    assert pa["inputs"]["terminal_g_pct"] == 2.5
    for inp in pa["editable_inputs"]:
        if inp["key"] == "wacc_pct":
            assert inp["value"] == 11.0
        if inp["key"] == "terminal_g_pct":
            assert inp["value"] == 2.5
