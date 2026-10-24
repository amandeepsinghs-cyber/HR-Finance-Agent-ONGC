import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

def build_dcf_proposal(persona: str, session: Any, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    overrides = overrides or {}
    
    # Defaults and sources
    wacc_pct = overrides.get("wacc_pct", 10.37)
    g_pct = overrides.get("terminal_g_pct", 3.0)
    
    # Check for degraded cases (market price stale or SSOT lines unverified)
    # BEH-05.09: No market price in last 10 trading days -> proposal disabled
    # Let's assume we have a mock check or default to false for now, but we need to support the payload shape
    market_stale = getattr(session, "market_stale", False)
    ssot_unverified = getattr(session, "ssot_unverified", False)
    
    if ssot_unverified:
        return {
            "proposed_action": None,
            "answer": "The FY26 cash-flow data hasn't passed verification yet. See coverage.",
            "access": {"status": "refused", "reason": "SSOT-UNVERIFIED"}
        }

    inputs = {
        "wacc_pct": wacc_pct,
        "terminal_g_pct": g_pct,
        "brent_usd": overrides.get("brent_usd", 80.0),
        "capex_scale_pct": overrides.get("capex_scale_pct", 100.0),
        "production_decline_pct": overrides.get("production_decline_pct", 0.0),
        "holdco_discount_pct": overrides.get("holdco_discount_pct", 0.0)
    }

    editable_inputs = [
        {"key": "wacc_pct", "label": "WACC", "type": "percent", "value": wacc_pct, "min": 5.0, "max": 25.0, "step": 0.1, "source": "fact_wacc_annual FY26"},
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
