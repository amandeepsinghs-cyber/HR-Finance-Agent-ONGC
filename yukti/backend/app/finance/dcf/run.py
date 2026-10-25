# run.py
from typing import Dict, Any, Optional
from app.finance.dcf.assumptions import DCFAssumptions
from app.finance.dcf.wacc import compute_wacc
from app.finance.dcf.fcff import compute_fcff
from app.finance.dcf.valuation import compute_valuation
from app.finance.dcf.sensitivity import compute_sensitivity, compute_tornado


def build_dcf_model_spec(dcf_res: Dict[str, Any], assumptions: Optional[DCFAssumptions] = None) -> Dict[str, Any]:
    """Formats run_dcf output into the SPEC-03 / DcfModelCard `visual.dcf_model` schema."""
    raw_fc = dcf_res.get("forecast", [])
    if isinstance(raw_fc, list):
        years = [str(r.get("period", f"FY{27 + i}")) for i, r in enumerate(raw_fc)]
        lines: Dict[str, Any] = {
            "fcff": [round(float(r.get("fcff", 0.0)), 2) for r in raw_fc],
            "discount_factor": [round(float(r.get("discount_factor", 0.0)), 4) for r in raw_fc],
            "pv_fcff": [round(float(r.get("pv_fcff", 0.0)), 2) for r in raw_fc],
        }
        if any("rev" in r for r in raw_fc):
            lines["revenue"] = [round(float(r.get("rev", 0.0)), 2) for r in raw_fc]
        if any("ebit" in r for r in raw_fc):
            lines["ebit"] = [round(float(r.get("ebit", 0.0)), 2) for r in raw_fc]
        forecast_spec: Dict[str, Any] = {"years": years, "lines": lines}
    else:
        forecast_spec = dict(raw_fc)

    raw_term = dict(dcf_res.get("terminal") or {})
    g_pct = (
        float(assumptions.terminal_g_pct.value)
        if assumptions is not None and hasattr(assumptions, "terminal_g_pct")
        else float(raw_term.get("g_pct", 3.0))
    )
    exit_mult = (
        float(assumptions.exit_ev_ebitda.value)
        if assumptions is not None and hasattr(assumptions, "exit_ev_ebitda")
        else float(raw_term.get("exit_multiple", 4.5))
    )
    raw_warn = raw_term.get("warning")
    warn_str = (
        "Gordon growth vs exit multiple divergence > 30%"
        if raw_warn is True
        else (raw_warn if isinstance(raw_warn, str) else None)
    )
    terminal_spec = {
        "method": str(raw_term.get("method") or "gordon"),
        "g_pct": g_pct,
        "tv_inr_cr": round(float(raw_term.get("tv_inr_cr", 0.0)), 2),
        "pv_tv_inr_cr": round(float(raw_term.get("pv_tv_inr_cr", 0.0)), 2),
        "exit_multiple": exit_mult,
        "tv_exit_inr_cr": round(float(raw_term.get("tv_exit_inr_cr", 0.0)), 2),
        "implied_g_pct": round(float(raw_term.get("implied_g_pct", 0.0)), 2),
        "warning": warn_str,
    }

    sens = dcf_res.get("sensitivity") or {}
    w_axis = [round(float(x), 4) for x in (sens.get("wacc_axis_pct") or [])]
    g_axis = [round(float(x), 4) for x in (sens.get("g_axis_pct") or [])]
    cells = [
        [round(float(c), 2) if c is not None else None for c in row]
        for row in (sens.get("values_inr") or [])
    ]
    sensitivity_grid_spec = {
        "row_input": {"name": "WACC", "unit": "%", "values": w_axis},
        "col_input": {"name": "Terminal g", "unit": "%", "values": g_axis},
        "output": {"name": "Value per share", "unit": "INR"},
        "cells": cells,
        "base": {"row_idx": len(w_axis) // 2, "col_idx": len(g_axis) // 2},
        "source": "SPEC-02 §8 DCF Engine",
    }

    iv = float((dcf_res.get("per_share") or {}).get("intrinsic_inr", 0.0))
    raw_tornado = dcf_res.get("tornado") or []
    if isinstance(raw_tornado, list):
        tornado_bars = [
            {
                "driver": str(b.get("driver", "")),
                "low_input": str(b.get("low_input") or "low"),
                "high_input": str(b.get("high_input") or "high"),
                "low_inr": round(float(b.get("low_inr", 0.0)), 2),
                "high_inr": round(float(b.get("high_inr", 0.0)), 2),
            }
            for b in raw_tornado
        ]
        tornado_spec = {
            "output": {"name": "Intrinsic value per share", "unit": "INR", "base": round(iv, 2)},
            "bars": tornado_bars,
            "source": "SPEC-02 §8 DCF Engine",
        }
    else:
        tornado_spec = dict(raw_tornado)

    return {
        "run_id": str(dcf_res.get("run_id") or "dcf_run"),
        "engine_version": str(dcf_res.get("engine_version") or "3.0"),
        "as_of": str(dcf_res.get("as_of") or ""),
        "scope": str(dcf_res.get("scope") or "standalone_sotp"),
        "assumptions": dcf_res.get("assumptions", {}),
        "per_share": dcf_res.get("per_share", {}),
        "wacc_build": dcf_res.get("wacc_build", {}),
        "forecast": forecast_spec,
        "terminal": terminal_spec,
        "bridge": dcf_res.get("bridge", []),
        "sensitivity": sens,
        "sensitivity_grid": sensitivity_grid_spec,
        "tornado": tornado_spec,
        "lineage_refs": dcf_res.get("lineage_refs", []),
        "provenance_label": str(dcf_res.get("provenance_label") or "illustrative"),
        "disclaimer": str(dcf_res.get("disclaimer") or "Illustrative valuation, not investment advice."),
    }


def run_dcf(assumptions: DCFAssumptions, fixture=None) -> Dict[str, Any]:
    wacc_build = compute_wacc(assumptions, fixture)
    fcff_res = compute_fcff(assumptions)
    val = compute_valuation(assumptions, fcff_res)
    sens = compute_sensitivity(assumptions, fcff_res, val)
    tornado = compute_tornado(assumptions, val.get("per_share", {}).get("intrinsic_inr", 0))

    lineage_refs = []
    if fixture is None:
        from app.finance.dcf.inputs import load_fy26_market_price_default, load_fy26_wacc_default
        w_val, w_src, w_meta = load_fy26_wacc_default()
        m_val, m_src, m_meta = load_fy26_market_price_default()
        lineage_refs = [
            {
                "item": f"WACC FY26 ({w_val}%)",
                "source": f"{w_src} (as_of={w_meta.get('as_of_date', '2026-03-31')}, method={w_meta.get('method_version', 'wacc-v1')})",
            },
            {
                "item": f"Market Price ONGC.NS (₹{m_val:.2f})",
                "source": f"{m_src} ({m_meta.get('source_url') or m_meta.get('source_doc', 'market_prices_seed.csv')})",
            },
        ]

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
        "lineage_refs": lineage_refs,
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
