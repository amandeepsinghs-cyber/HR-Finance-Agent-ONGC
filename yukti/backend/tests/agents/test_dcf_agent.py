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

def test_dcf_proposal_unverified(monkeypatch, tmp_path):
    """P5.6 D1: Missing or unverified fact_snapshot refuses honestly without literal fallback."""
    from app.finance.dcf import inputs as dcf_inputs

    monkeypatch.setattr(dcf_inputs, "SNAPSHOT_PARQUET", tmp_path / "missing_snapshot.parquet")
    sess = MockSession()
    res = build_dcf_proposal("DIR_FIN", sess)
    assert res["proposed_action"] is None
    assert "fact_snapshot" in res["answer"]
    assert "hasn't passed verification yet" in res["answer"]
    assert res["access"]["status"] == "refused"
    assert res["access"]["reason"] == "SSOT-UNVERIFIED"
    assert res["access"]["missing_input"] == "fact_snapshot"


def test_dcf_proposal_missing_wacc_and_market_price_refuses(monkeypatch, tmp_path):
    """P5.6 D1: Missing fact_wacc_annual, NULL wacc_pct row, or missing market_prices_seed.csv + fact_wacc_input refuses honestly."""
    from app.finance.dcf import inputs as dcf_inputs

    sess = MockSession()

    # 1. Missing fact_wacc_annual.parquet -> refuses naming fact_wacc_annual
    monkeypatch.setattr(dcf_inputs, "WACC_ANNUAL_PARQUET", tmp_path / "missing_wacc.parquet")
    res_wacc = build_dcf_proposal("DIR_FIN", sess)
    assert res_wacc["proposed_action"] is None
    assert "fact_wacc_annual" in res_wacc["answer"]
    assert res_wacc["access"]["status"] == "refused"
    assert res_wacc["access"]["missing_input"] == "fact_wacc_annual"

    # 2. NULL wacc_pct row in fact_wacc_annual -> refuses naming fact_wacc_annual
    monkeypatch.setattr(
        dcf_inputs,
        "load_wacc_annual_rows",
        lambda: [{"fy": "FY26", "wacc_pct": None, "provenance_label": "verified"}],
    )
    res_null_wacc = build_dcf_proposal("DIR_FIN", sess)
    assert res_null_wacc["proposed_action"] is None
    assert "fact_wacc_annual" in res_null_wacc["answer"]
    assert res_null_wacc["access"]["status"] == "refused"
    assert res_null_wacc["access"]["missing_input"] == "fact_wacc_annual"


def test_dcf_proposal_missing_market_price_refuses(monkeypatch, tmp_path):
    """P5.6 D1: Missing market_prices_seed.csv and fact_wacc_input.parquet refuses honestly."""
    from app.finance.dcf import inputs as dcf_inputs

    monkeypatch.setattr(dcf_inputs, "MARKET_SEED_CSV", tmp_path / "missing_seed.csv")
    monkeypatch.setattr(dcf_inputs, "WACC_INPUT_PARQUET", tmp_path / "missing_wacc_input.parquet")
    sess = MockSession()
    res = build_dcf_proposal("DIR_FIN", sess)
    assert res["proposed_action"] is None
    assert "market_prices_seed.csv" in res["answer"]
    assert res["access"]["status"] == "refused"
    assert "market_prices_seed.csv" in res["access"]["missing_input"]


@pytest.mark.asyncio
async def test_dcf_job_runner():
    async def mock_emit(step, msg, prog):
        pass
    res = await dcf_job_runner("test_job_123", {"inputs": {"wacc_pct": 11.6556}}, "sess_1", mock_emit)
    assert res["contract_version"] == 3
    assert res["turn_id"] == "job:test_job_123"
    assert res["visual"]["type"] == "dcf_model"
    assert "dcf_model" in res["visual"]
    assert "years" in res["visual"]["dcf_model"]["forecast"]
    assert "sensitivity_grid" in res["visual"]["dcf_model"]
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
