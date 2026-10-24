import asyncio
from typing import Dict, Any, Callable, Awaitable
from datetime import datetime, timezone
import uuid

from app.jobs.executor import get_executor
from app.finance.dcf.run import run_dcf
from app.finance.dcf.assumptions import DCFAssumptions, AssumptionField
from app.finance.dcf.xlsx_writer import write_dcf_xlsx

async def dcf_job_runner(job_id: str, payload: Dict[str, Any], session_id: str, emit_progress: Callable[[str, str, float], Awaitable[None]]) -> Dict[str, Any]:
    # load_inputs → wacc_build → forecast → valuation → sensitivity_grid → tornado → xlsx → publish
    await emit_progress("load_inputs", "Loading inputs", 0.1)
    await asyncio.sleep(0.1)
    
    inputs = payload.get("inputs", {})
    
    def mk(val):
        return AssumptionField(value=val, source="job")

    asm = DCFAssumptions(
        wacc_pct=mk(inputs.get("wacc_pct", 10.37)),
        terminal_g_pct=mk(inputs.get("terminal_g_pct", 3.0)),
        brent_usd=mk(inputs.get("brent_usd", 80.0)),
        capex_scale_pct=mk(inputs.get("capex_scale_pct", 100.0)),
        production_decline_pct=mk(inputs.get("production_decline_pct", 0.0)),
        holdco_discount_pct=mk(inputs.get("holdco_discount_pct", 0.0)),
        exit_ev_ebitda=mk(5.0),
        as_of=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        run_id=job_id,
        shares_outstanding=mk(1258.0279206),
        market_price_inr=mk(300.0),
        listed_investments_inr_cr=mk(300.0), # mock
        unlisted_investments_inr_cr=mk(0.0),
        cash_and_equivalents_inr_cr=mk(0.0),
        srf_deposits_inr_cr=mk(32727.7),
        decom_provision_inr_cr=mk(0.0),
        borrowings_inr_cr=mk(7823.4),
        lease_liab_inr_cr=mk(25821.8),
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
        forecast_fcff=[]
    )
    
    await emit_progress("wacc_build", "Building WACC", 0.2)
    # The actual run_dcf computes wacc, fcff, valuation, sensitivity, tornado
    # We will simulate the steps via progress.
    # To be precise, run_dcf does it all at once, so we'll just yield progress.
    
    res = run_dcf(asm)
    await emit_progress("forecast", "Forecasting FCFF", 0.4)
    await emit_progress("valuation", "Computing valuation", 0.5)
    await emit_progress("sensitivity_grid", "Computing sensitivity", 0.7)
    await emit_progress("tornado", "Computing tornado", 0.8)
    
    await emit_progress("xlsx", "Generating XLSX", 0.9)
    from app.config import EXPORTS_DIR
    import os
    if not os.path.exists(EXPORTS_DIR):
        os.makedirs(EXPORTS_DIR)
        
    xlsx_path = os.path.join(EXPORTS_DIR, f"ONGC_DCF_{job_id}.xlsx")
    write_dcf_xlsx(res, xlsx_path)
    
    await emit_progress("publish", "Publishing results", 1.0)
    
    iv = res.get("per_share", {}).get("intrinsic_inr", 0)
    px = 300.0 # mock
    upside = (iv / px - 1) * 100 if px else 0
    verdict = "undervalued" if upside > 10 else ("overvalued" if upside < -10 else "fairly valued")
    
    summary = f"The DCF valuation is ready. Intrinsic value is ₹{iv:.2f} per share against a market price of ₹{px:.2f}, so the model suggests ONGC is {verdict} by {abs(upside):.1f}%. This is an illustrative valuation, not investment advice."
    
    contract = {
        "contract_version": 3,
        "turn_id": f"job:{job_id}",
        "visual": {
            "type": "dcf_model",
            "dcf_model": res
        },
        "provenance": {
            "label": "illustrative"
        },
        "spoken_summary": summary,
        "caveat": "This is an illustrative valuation, not investment advice.",
        "export_options": ["xlsx", "pdf"],
        "artifacts": [
            {
                "export_id": job_id,
                "kind": "xlsx",
                "filename": f"ONGC_DCF_{job_id}.xlsx"
            }
        ]
    }
    
    return contract

def init_dcf_agent():
    executor = get_executor()
    if executor:
        executor.register_agent_runner("dcf_agent", dcf_job_runner)

class DCFAgent:
    def __init__(self):
        init_dcf_agent()
