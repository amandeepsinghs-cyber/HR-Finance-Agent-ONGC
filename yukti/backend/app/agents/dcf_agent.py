import asyncio
import os
from typing import Dict, Any, Callable, Awaitable

from app.jobs.executor import get_executor
from app.finance.dcf.run import run_dcf
from app.finance.dcf.assumptions import DCFAssumptions, AssumptionField, defaults_from_ssot
from app.finance.dcf.inputs import (
    load_fy26_market_price_default,
    load_fy26_wacc_default,
    load_ssot_snapshot_rows,
    load_wacc_annual_rows,
)
from app.finance.dcf.xlsx_writer import write_dcf_xlsx


def build_dcf_assumptions_from_inputs(job_id: str, inputs: Dict[str, Any]) -> DCFAssumptions:
    inputs = inputs or {}
    default_wacc_pct, wacc_src, _ = load_fy26_wacc_default()
    default_mkt_px, mkt_src, mkt_meta = load_fy26_market_price_default()
    as_of = str(mkt_meta.get("date") or "2026-03-30")

    base = defaults_from_ssot(load_ssot_snapshot_rows(), load_wacc_annual_rows(), as_of=as_of)
    updates: Dict[str, Any] = {
        "run_id": job_id,
        "as_of": as_of,
        "market_price_inr": AssumptionField(
            value=float(inputs.get("market_price_inr", default_mkt_px)),
            source=mkt_src,
            edited_by_user="market_price_inr" in inputs,
        ),
        "wacc_pct": AssumptionField(
            value=float(inputs.get("wacc_pct", default_wacc_pct)),
            source=wacc_src if "wacc_pct" not in inputs else f"user override (base: {wacc_src})",
            edited_by_user="wacc_pct" in inputs,
        ),
    }
    for key in ("terminal_g_pct", "brent_usd", "capex_scale_pct", "production_decline_pct", "holdco_discount_pct"):
        if key in inputs and inputs[key] is not None:
            orig_field = getattr(base, key)
            updates[key] = AssumptionField(
                value=float(inputs[key]),
                source=orig_field.source,
                edited_by_user=True,
            )
    return base.model_copy(update=updates)


async def dcf_job_runner(
    job_id: str,
    payload: Dict[str, Any],
    session_id: str,
    emit_progress: Callable[[str, str, float], Awaitable[None]],
) -> Dict[str, Any]:
    # load_inputs → wacc_build → forecast → valuation → sensitivity_grid → tornado → xlsx → publish
    await emit_progress("load_inputs", "Loading inputs", 0.1)
    await asyncio.sleep(0.05)

    inputs = payload.get("inputs", {})
    asm = build_dcf_assumptions_from_inputs(job_id, inputs)

    await emit_progress("wacc_build", "Building WACC", 0.2)
    res = run_dcf(asm)
    await emit_progress("forecast", "Forecasting FCFF", 0.4)
    await emit_progress("valuation", "Computing valuation", 0.5)
    await emit_progress("sensitivity_grid", "Computing sensitivity", 0.7)
    await emit_progress("tornado", "Computing tornado", 0.8)

    await emit_progress("xlsx", "Generating XLSX", 0.9)
    from app.config import EXPORTS_DIR
    if not os.path.exists(EXPORTS_DIR):
        os.makedirs(EXPORTS_DIR)

    xlsx_path = os.path.join(EXPORTS_DIR, f"ONGC_DCF_{job_id}.xlsx")
    write_dcf_xlsx(res, xlsx_path)

    await emit_progress("publish", "Publishing results", 1.0)

    iv = float(res.get("per_share", {}).get("intrinsic_inr", 0.0))
    px = float(res.get("per_share", {}).get("market_inr", asm.market_price_inr.value))
    mkt_date = str(res.get("per_share", {}).get("market_date", asm.as_of))
    upside = (iv / px - 1) * 100 if px else 0.0
    verdict = "undervalued" if upside > 10 else ("overvalued" if upside < -10 else "fairly valued")

    summary = (
        f"The DCF valuation is ready (illustrative valuation). Intrinsic value is ₹{iv:.2f} per share against "
        f"a market price of ₹{px:.2f} (NSE close {mkt_date}), so the model suggests ONGC is {verdict} "
        f"by {abs(upside):.1f}%. Illustrative valuation, not investment advice."
    )

    contract = {
        "contract_version": 3,
        "turn_id": f"job:{job_id}",
        "language": "en",
        "spoken_summary": summary,
        "display_text": summary,
        "visual": {
            "type": "dcf_model",
            "mode": "replace",
            "title": "ONGC Standalone DCF Valuation (Illustrative)",
            "dcf_model": res,
        },
        "access": {"status": "allowed"},
        "sources": [
            {"kind": "data", "object": "hrfin_gold.fact_wacc_annual", "title": "ONGC WACC SSOT FY26"},
            {"kind": "data", "object": "market_prices_seed.csv", "title": f"NSE Bhavcopy ONGC.NS ({mkt_date})"},
        ],
        "provenance": {
            "label": "illustrative",
            "detail": "Illustrative valuation, not investment advice.",
        },
        "caveat": "This is an illustrative valuation, not investment advice.",
        "export_options": ["xlsx", "pdf"],
        "artifacts": [
            {
                "export_id": job_id,
                "kind": "xlsx",
                "filename": f"ONGC_DCF_{job_id}.xlsx",
            }
        ],
    }

    return contract


def init_dcf_agent():
    executor = get_executor()
    if executor:
        executor.register_agent_runner("dcf_agent", dcf_job_runner)


class DCFAgent:
    def __init__(self):
        init_dcf_agent()
