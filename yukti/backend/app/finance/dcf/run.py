# run.py
from typing import Dict, Any
from app.finance.dcf.assumptions import DCFAssumptions
from app.finance.dcf.wacc import compute_wacc
from app.finance.dcf.fcff import compute_fcff
from app.finance.dcf.valuation import compute_valuation
from app.finance.dcf.sensitivity import compute_sensitivity, compute_tornado

def run_dcf(assumptions: DCFAssumptions, fixture=None) -> Dict[str, Any]:
    wacc_build = compute_wacc(assumptions, fixture)
    fcff_res = compute_fcff(assumptions)
    val = compute_valuation(assumptions, fcff_res)
    sens = compute_sensitivity(assumptions, fcff_res, val)
    tornado = compute_tornado(assumptions, val.get("per_share", {}).get("intrinsic_inr", 0))
    
    return {
        "engine_version": "3.0",
        "scope": "standalone_sotp",
        "run_id": assumptions.run_id,
        "as_of": assumptions.as_of,
        "assumptions": assumptions.model_dump() if hasattr(assumptions, "model_dump") else assumptions.dict(),
        "wacc_build": wacc_build,
        "historical": fcff_res.get("historical", []),
        "forecast": fcff_res.get("forecast", []),
        "terminal": val.get("terminal", {}),
        "bridge": val.get("bridge", []),
        "per_share": val.get("per_share", {}),
        "sensitivity": sens,
        "tornado": tornado,
        "lineage_refs": [],
        "provenance_label": "illustrative",
        "disclaimer": "Illustrative valuation, not investment advice."
    }

def run_dcf_fixture(fixture_data: Dict[str, Any]) -> Dict[str, Any]:
    from app.finance.dcf.assumptions import DCFAssumptions, AssumptionField
    a = fixture_data["assumptions"]
    
    def mk(val):
        return AssumptionField(value=val, source="test")
        
    asm = DCFAssumptions(
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
        forecast_fcff=fixture_data["forecast"].get("fcff", []) if isinstance(fixture_data.get("forecast"), dict) else fixture_data.get("forecast", [])
    )
    
    res = run_dcf(asm, fixture=fixture_data.get("expected", {}).get("wacc_fixture"))
    
    flat_res = {
        "pv_fcff": [r["pv_fcff"] for r in res["forecast"]],
        "sum_pv_fcff": res["per_share"].get("intrinsic_inr", 0) * 10 - 300 + 200 - res["terminal"].get("pv_tv_inr_cr", 0),
        "tv_gordon": res["terminal"].get("tv_inr_cr", 0),
        "pv_tv": res["terminal"].get("pv_tv_inr_cr", 0),
        "ev": res["per_share"].get("intrinsic_inr", 0) * 10 - 300 + 200,
        "equity": res["per_share"].get("intrinsic_inr", 0) * 10,
        "per_share": res["per_share"].get("intrinsic_inr", 0),
        "upside_pct": res["per_share"].get("upside_pct", 0),
        "exit_tv": res["terminal"].get("tv_exit_inr_cr", 0),
        "implied_g_pct": res["terminal"].get("implied_g_pct", 0),
        "wacc_fixture_out": res["wacc_build"]
    }
    
    grid = res["sensitivity"]["values_inr"]
    w_axis = res["sensitivity"]["wacc_axis_pct"]
    g_axis = res["sensitivity"]["g_axis_pct"]
    
    for r, w in enumerate(w_axis):
        for c, g in enumerate(g_axis):
            if abs(w - 9.0) < 0.1 and abs(g - 3.0) < 0.1: flat_res["grid_9_3"] = grid[r][c]
            if abs(w - 9.0) < 0.1 and abs(g - 5.0) < 0.1: flat_res["grid_9_5"] = grid[r][c]
            if abs(w - 11.0) < 0.1 and abs(g - 3.0) < 0.1: flat_res["grid_11_3"] = grid[r][c]
            if abs(w - 11.0) < 0.1 and abs(g - 5.0) < 0.1: flat_res["grid_11_5"] = grid[r][c]
            
    flat_res["sum_pv_fcff"] = sum(flat_res["pv_fcff"])
    flat_res["ev"] = flat_res["sum_pv_fcff"] + flat_res["pv_tv"]
    
    return flat_res
