import pytest
import json
import os
from unittest.mock import patch
from app.finance.dcf.run import run_dcf_fixture, run_dcf
from app.finance.dcf.assumptions import defaults_from_ssot

@pytest.fixture
def dcf_fixture_data():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "dcf_fixture.json")
    with open(path, "r") as f:
        return json.load(f)

def test_fixture_values(dcf_fixture_data):
    result = run_dcf_fixture(dcf_fixture_data)
    expected = dcf_fixture_data["expected"]
    
    assert result["pv_fcff"] == expected["pv_fcff"]
    assert abs(result["sum_pv_fcff"] - expected["sum_pv_fcff"]) <= 1e-4
    assert abs(result["tv_gordon"] - expected["tv_gordon"]) <= 1e-4
    assert abs(result["pv_tv"] - expected["pv_tv"]) <= 1e-4
    assert abs(result["ev"] - expected["ev"]) <= 1e-4
    assert abs(result["equity"] - expected["equity"]) <= 1e-4
    assert abs(result["per_share"] - expected["per_share"]) <= 1e-4
    assert abs(result["upside_pct"] - expected["upside_pct"]) <= 1e-2
    assert abs(result["exit_tv"] - expected["exit_tv"]) <= 1e-4
    assert abs(result["implied_g_pct"] - expected["implied_g_pct"]) <= 1e-3
    assert abs(result["grid_9_3"] - expected["grid_9_3"]) <= 1e-4
    assert abs(result["grid_9_5"] - expected["grid_9_5"]) <= 1e-4
    assert abs(result["grid_11_3"] - expected["grid_11_3"]) <= 1e-4
    assert abs(result["grid_11_5"] - expected["grid_11_5"]) <= 1e-4
    
    wout = result["wacc_fixture_out"]
    wexp = expected["wacc_fixture"]
    assert abs(wout["beta_adj"] - wexp["beta_adj"]) <= 1e-4
    assert abs(wout["ke"] - wexp["ke"]) <= 1e-4
    assert abs(wout["kd_after_tax"] - wexp["kd_after_tax"]) <= 1e-4
    assert abs(wout["wacc"] - wexp["wacc"]) <= 1e-4
    assert abs(wout["ke_alt"] - wexp["ke_alt"]) <= 1e-4
    assert abs(wout["wacc_alt"] - wexp["wacc_alt"]) <= 1e-4

def test_tv_guard(dcf_fixture_data):
    dcf_fixture_data["assumptions"]["wacc_pct"] = 4.0
    dcf_fixture_data["assumptions"]["g_pct"] = 4.0
    with pytest.raises(ValueError, match="E_TV_GUARD"):
        run_dcf_fixture(dcf_fixture_data)

def test_purity():
    # Mocks raising on LLM/network
    with patch("httpx.AsyncClient.request", side_effect=Exception("Network call not allowed")), \
         patch("google.genai.Client", side_effect=Exception("LLM call not allowed")):
        a = defaults_from_ssot([], [], "2026-10-23")
        res = run_dcf(a)
        assert res["provenance_label"] == "illustrative"

def test_determinism():
    a1 = defaults_from_ssot([], [], "2026-10-23")
    r1 = json.dumps(run_dcf(a1), sort_keys=True)
    
    a2 = defaults_from_ssot([], [], "2026-10-23")
    r2 = json.dumps(run_dcf(a2), sort_keys=True)
    
    assert r1 == r2

def test_poisoned_row_rejection():
    # Only verified=True should be used
    snapshot = [
        {"line_code": "INV.LISTED", "value_inr_cr": 1000.0, "verified": True},
        {"line_code": "INV.UNLISTED", "value_inr_cr": 5000.0, "verified": False}
    ]
    
    a = defaults_from_ssot(snapshot, [], "2026-10-23")
    assert a.listed_investments_inr_cr.value == 1000.0
    assert a.unlisted_investments_inr_cr.value == 0.0
