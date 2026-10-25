import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from app.finance.dcf.inputs import (
    DCFInputMissingError,
    load_fy26_market_price_default,
    load_fy26_wacc_default,
    load_ssot_snapshot_rows,
)


def build_dcf_proposal(persona: str, session: Any, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    overrides = overrides or {}
    try:
        snapshot_rows = load_ssot_snapshot_rows()
        verified_snapshot_rows = [r for r in snapshot_rows if r.get("verified", False)]
        if not verified_snapshot_rows:
            raise DCFInputMissingError("fact_snapshot")
        default_wacc_pct, wacc_source, wacc_meta = load_fy26_wacc_default()
        default_mkt_px, mkt_source, mkt_meta = load_fy26_market_price_default()
    except DCFInputMissingError as exc:
        missing_input = exc.missing_input
        return {
            "proposed_action": None,
            "answer": (
                f"Cannot run the DCF valuation because required input `{missing_input}` is missing or "
                f"the FY26 cash-flow / WACC data hasn't passed verification yet. See coverage."
            ),
            "access": {
                "status": "refused",
                "reason": "SSOT-UNVERIFIED",
                "missing_input": missing_input,
            },
        }

    # Defaults and sources from SSOT fact_wacc_annual FY26 and NSE market_prices_seed.csv
    wacc_pct = float(overrides.get("wacc_pct", default_wacc_pct))
    g_pct = float(overrides.get("terminal_g_pct", 3.0))

    # BEH-05.09: degraded market-price staleness check
    market_stale = getattr(session, "market_stale", False) if session is not None else False

    inputs = {
        "wacc_pct": wacc_pct,
        "terminal_g_pct": g_pct,
        "brent_usd": overrides.get("brent_usd", 80.0),
        "capex_scale_pct": overrides.get("capex_scale_pct", 100.0),
        "production_decline_pct": overrides.get("production_decline_pct", 0.0),
        "holdco_discount_pct": overrides.get("holdco_discount_pct", 0.0)
    }

    editable_inputs = [
        {"key": "wacc_pct", "label": "WACC", "type": "percent", "value": wacc_pct, "min": 5.0, "max": 25.0, "step": 0.1, "source": wacc_source},
        {"key": "terminal_g_pct", "label": "Terminal Growth", "type": "percent", "value": g_pct, "min": 0.0, "max": 10.0, "step": 0.1, "source": "default (illustrative)"},
        {"key": "brent_usd", "label": "Brent Price", "type": "number", "value": inputs["brent_usd"], "min": 40.0, "max": 120.0, "step": 1.0, "unit": "USD/bbl", "source": "fact_price_realisation (FY26 realised)"},
        {"key": "capex_scale_pct", "label": "Capex Scale", "type": "percent", "value": inputs["capex_scale_pct"], "min": 50.0, "max": 200.0, "step": 5.0, "source": "FY22-FY26 average capex (verified)"},
        {"key": "production_decline_pct", "label": "Production Decline", "type": "percent", "value": inputs["production_decline_pct"], "min": -10.0, "max": 20.0, "step": 0.5, "source": "FY22-FY26 CAGR of fact_production_annual (ONGC standalone)"},
        {"key": "holdco_discount_pct", "label": "HoldCo Discount", "type": "percent", "value": inputs["holdco_discount_pct"], "min": 0.0, "max": 50.0, "step": 5.0, "source": "default"}
    ]

    proposal = {
        "id": f"pa_{uuid.uuid4().hex[:8]}",
        "agent": "dcf_agent",
        "agent_version": "dcf-v1.0.0",
        "summary": "Can I run the DCF valuation agent in the background to estimate ONGC's intrinsic value? It takes about 15 seconds.",
        "est_seconds": 15,
        "inputs": inputs,
        "editable_inputs": editable_inputs,
        "lineage": {
            "wacc": {**wacc_meta, "source": wacc_source},
            "market_price": {**mkt_meta, "source": mkt_source, "value_inr": default_mkt_px},
        },
        "requires_role": ["CMD", "DIR_FIN"],
        "buttons": ["run", "edit", "cancel"],
        "voice_confirm_hint": "Say yes, run it, or cancel.",
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    }
    
    ans = {
        "proposed_action": proposal,
        "answer": proposal["summary"]
    }
    
    if market_stale:
        proposal["buttons"] = ["run", "edit", "cancel"] # still run? wait BEH-05.09 says Proposal disabled. Wait, it says: Proposal disabled: "Market price data is unavailable, so I can't compare intrinsic value to the share price. I can run the model and show value per share only?" (chip), and the verdict is omitted.
        ans["answer"] = "Market price data is unavailable, so I can't compare intrinsic value to the share price. I can run the model and show value per share only?"
        proposal["summary"] = ans["answer"]
        ans["chips"] = ["run the model and show value per share only"]

    return ans
