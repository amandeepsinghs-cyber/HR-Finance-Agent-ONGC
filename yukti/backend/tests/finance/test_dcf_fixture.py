import pytest
import json
import os
from unittest.mock import patch
from app.finance.dcf.run import run_dcf
from app.finance.dcf.assumptions import defaults_from_ssot, DCFAssumptions, AssumptionField

@pytest.fixture
def dcf_fixture_data():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "dcf_fixture.json")
    with open(path, "r") as f:
        return json.load(f)

def _build_asm(a, fixture_data):
    def mk(val):
        return AssumptionField(value=val, source="test")
    return DCFAssumptions(
        wacc_pct=mk(a["wacc_pct"]),
        terminal_g_pct=mk(a["g_pct"]),
        brent_usd=mk(80.0),
        capex_scale_pct=mk(100.0),
        production_decline_pct=mk(0.0),
        holdco_discount_pct=mk(0.0),
        exit_ev_ebitda=mk(5.0),
        as_of="2026-10-23",
        run_id="test",
        shares_outstanding=mk(10.0),
        listed_investments_inr_cr=mk(300.0),
        unlisted_investments_inr_cr=mk(0.0),
        cash_and_equivalents_inr_cr=mk(0.0),
        srf_deposits_inr_cr=mk(0.0),
        decom_provision_inr_cr=mk(0.0),
        borrowings_inr_cr=mk(200.0),
        lease_liab_inr_cr=mk(0.0),
        vol_crude_mmt=mk(0),
        vol_gas_bcm=mk(0),
        bbl_per_tonne=mk(0),
        gcv_mmbtu_per_scm=mk(0),
        fx_inr_usd=mk(0),
        crude_realisation_discount_pct=mk(0),
        gas_price_usd_mmbtu=mk(0),
        vap_revenue_ratio=mk(0),
        effective_levy_rate=mk(0),
        opex_per_boe=mk(0),
        inflation_pct=mk(0),
        exploration_writeoff_ratio=mk(0),
        dd_a_ratio=mk(0),
        tax_rate_pct=mk(25.17),
        capex_base_inr_cr=mk(0),
        nwc_pct=mk(0),
        market_price_inr=mk(150.0),
        forecast_fcff=fixture_data["forecast"].get("fcff", []) if isinstance(fixture_data.get("forecast"), dict) else fixture_data.get("forecast", [])
    )

def test_fixture_values(dcf_fixture_data):
    a = dcf_fixture_data["assumptions"]
    asm = _build_asm(a, dcf_fixture_data)
    
    res = run_dcf(asm, fixture=dcf_fixture_data.get("expected", {}).get("wacc_fixture"))
    expected = dcf_fixture_data["expected"]
    
    pv_fcffs = [r["pv_fcff"] for r in res["forecast"]]
    for out_val, exp_val in zip(pv_fcffs, expected["pv_fcff"]):
        assert abs(out_val - exp_val) <= 1e-4

    sum_pv_fcff = sum(pv_fcffs)
    assert abs(sum_pv_fcff - expected["sum_pv_fcff"]) <= 1e-4
    
    term = res["terminal"]
    assert abs(term["tv_inr_cr"] - expected["tv_gordon"]) <= 1e-4
    assert abs(term["pv_tv_inr_cr"] - expected["pv_tv"]) <= 1e-4
    
    ev = sum_pv_fcff + term["pv_tv_inr_cr"]
    assert abs(ev - expected["ev"]) <= 1e-4
    
    equity = ev - 200 + 300
    assert abs(res["per_share"]["intrinsic_inr"]*10 - expected["equity"]) <= 1e-4
    assert abs(res["per_share"]["intrinsic_inr"] - expected["per_share"]) <= 1e-4
    assert abs(res["per_share"]["upside_pct"] - expected["upside_pct"]) <= 1e-2
    assert res["per_share"]["verdict"] == "undervalued"
    
    assert abs(term["tv_exit_inr_cr"] - expected["exit_tv"]) <= 1e-4
    assert abs(term["implied_g_pct"] - expected["implied_g_pct"]) <= 1e-3
    
    wout = res["wacc_build"]
    wexp = expected["wacc_fixture"]
    assert abs(wout["beta_adj"] - wexp["beta_adj"]) <= 1e-4
    assert abs(wout["ke_pct"] - wexp["ke"]) <= 1e-4
    assert abs(wout["kd_after_tax_pct"] - wexp["kd_after_tax"]) <= 1e-4
    assert abs(wout["wacc_pct"] - wexp["wacc"]) <= 1e-4
    
    # Optional ke_alt and wacc_alt based on ke/wacc calculations
    assert "wacc_alt_gsec_less_spread_pct" in wout
    # 9x9 grid test
    grid = res["sensitivity"]["values_inr"]
    w_axis = res["sensitivity"]["wacc_axis_pct"]
    g_axis = res["sensitivity"]["g_axis_pct"]
    
    for r, w in enumerate(w_axis):
        for c, g in enumerate(g_axis):
            if w - g < 1.0:
                assert grid[r][c] is None
            else:
                if abs(w - 9.0) < 0.1 and abs(g - 3.0) < 0.1: assert abs(grid[r][c] - expected["grid_9_3"]) <= 1e-4
                if abs(w - 9.0) < 0.1 and abs(g - 5.0) < 0.1: assert abs(grid[r][c] - expected["grid_9_5"]) <= 1e-4
                if abs(w - 11.0) < 0.1 and abs(g - 3.0) < 0.1: assert abs(grid[r][c] - expected["grid_11_3"]) <= 1e-4
                if abs(w - 11.0) < 0.1 and abs(g - 5.0) < 0.1: assert abs(grid[r][c] - expected["grid_11_5"]) <= 1e-4

def test_tv_guard(dcf_fixture_data):
    a = dcf_fixture_data["assumptions"]
    a["wacc_pct"] = 4.0
    a["g_pct"] = 4.0
    asm = _build_asm(a, dcf_fixture_data)
    with pytest.raises(ValueError, match="E_TV_GUARD"):
        run_dcf(asm)

def test_tornado_and_ssot_defaults():
    # AC-07 bridge sources test, tornado sorting, real ssot rows populated
    snapshot = [
        {"line_code": "BS.CCE", "value_inr_cr": 83.511, "verified": True},
        {"line_code": "BS.OTHER_BANK_BAL", "value_inr_cr": 28576.74, "verified": True},
        {"line_code": "BS.BORROW_NC", "value_inr_cr": 3803.401, "verified": True},
        {"line_code": "BS.BORROW_CUR", "value_inr_cr": 4020.0, "verified": True},
        {"line_code": "PL.REV_OPS", "value_inr_cr": 132508.136, "verified": True},
    ]
    wacc_table = [{"fiscal_year": "FY26", "wacc_pct": 10.5, "verified": True}]
    
    a = defaults_from_ssot(snapshot, wacc_table, "2026-10-23")
    res = run_dcf(a)
    
    assert len(res["forecast"]) == 10
    assert res["forecast"][0]["period"] == "FY27"
    assert res["forecast"][-1]["period"] == "FY36"
    
    # Tornado
    tornado = res["tornado"]
    assert len(tornado) == 8
    
    # Bridge
    bridge = res["bridge"]
    for row in bridge:
        assert row["source"] != ""

def test_purity():
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
    snapshot = [
        {"line_code": "BS.INVESTMENTS_NC", "value_inr_cr": 1000.0, "verified": True},
        {"line_code": "BS.INVESTMENTS_C", "value_inr_cr": 5000.0, "verified": False}
    ]
    a = defaults_from_ssot(snapshot, [], "2026-10-23")
    assert a.listed_investments_inr_cr.value == 1000.0
    assert a.unlisted_investments_inr_cr.value == 0.0
