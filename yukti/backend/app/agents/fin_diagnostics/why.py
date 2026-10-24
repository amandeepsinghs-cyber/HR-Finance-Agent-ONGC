import logging
import time
import re
from typing import Any, Dict, Optional, List

from app.brain.query_spec import QuerySpec
from app.brain.planner import Plan
from app.brain.compiler import get_compiler
from app.agents.fin_diagnostics.variance import pbt_bridge, attribute, _prev_fy
from app.knowledge.ar_retriever import ARRetriever
from app.brain.grounding import check_numeric_grounding
from app.brain.narrator import compose_spoken

logger = logging.getLogger(__name__)

async def run_why_turn(
    query: str,
    plan: Plan,
    prev: Optional[QuerySpec],
    session_state: Any,
    persona: str,
    turn_id: str,
    language: str,
    t0: float,
) -> Dict[str, Any]:
    spec = plan.spec
    fy_to = (spec.period.fy if spec.period else None) or "FY26"
    fy_from = _prev_fy(fy_to)
    
    # Map spec metric to line_code
    line_code = "PL.PBT"
    if spec.metric in ("corporate_revenue_cr", "revenue"):
        line_code = "PL.REV_OPS"
    elif spec.metric in ("corporate_pat_cr", "pat_cr"):
        line_code = "PL.PAT"
    
    # Also extract line_item filter if any
    for f in spec.filters:
        if f.field == "line_item":
            # For simplicity, if they asked a specific line item, we just use its canonical code
            # We don't have the exact code mapping here, but we can assume PL.REV_OPS etc.
            pass

    scope = "standalone" # default
    # extract scope from filters if present
    for f in spec.filters:
        if f.field == "scope" and f.values:
            scope = str(f.values[0])
            
    compiler = get_compiler()
    # Get the latest df to run variance against
    # We can fetch the raw data from v_fin_statement_as_reported or use _latest_df
    # In compiler.py, _latest_df() is a synchronous/cached call
    df = compiler._latest_df()

    # 1. Variance Engine
    if line_code in ("PL.PBT", "PL.PAT"):
        bridge = pbt_bridge(df, fy_to=fy_to, fy_from=fy_from, scope=scope)
        rows = bridge.rows
        start_val = bridge.start
        end_val = bridge.end
    else:
        rows = attribute(df, line_code, fy_to=fy_to, fy_from=fy_from, scope=scope)
        bridge = None
        # dummy start/end since attribute doesn't return Bridge
        start_val = 0
        end_val = sum(r.impact_inr_cr for r in rows)

    # Allowed numbers
    allowed = set()
    if bridge:
        allowed.add(bridge.start)
        allowed.add(bridge.end)
        allowed.add(bridge.delta)
    for r in rows:
        allowed.add(r.delta_inr_cr)
        allowed.add(r.impact_inr_cr)
        allowed.add(r.impact_on_pbt_inr_cr)
        for i in r.inputs:
            v = i.get("value")
            if isinstance(v, (int, float)):
                allowed.add(float(v))

    # Top drivers
    top_drivers = rows[:3]
    top_line_codes = [r.line_code for r in top_drivers]
    
    # 2. AR Retrieval
    retriever = ARRetriever()
    chunks = retriever.retrieve(
        question=query, 
        fiscal_year=fy_to,
        line_code=top_line_codes[0] if top_line_codes else None,
        sections=["mdna", "directors_report", "notes"],
        top_k=3
    )

    # 3. Generate narrative (simulate LLM with templated text for now or call LLM?)
    # Packet says: "The narrator (LLM) may paraphrase or quote them..."
    # If we need an LLM, let's call one, or just compose deterministically.
    # The packet says: "Templated text; numbers inserted from rows." for the Lead.
    
    lead = []
    if bridge:
        lead.append(f"PBT changed by {bridge.delta:.1f} crore ({bridge.start:.1f} to {bridge.end:.1f}).")
    for d in top_drivers:
        lead.append(f"{d.line_code} had an impact of {d.impact_on_pbt_inr_cr:.1f} crore.")
        
    for c in chunks:
        lead.append(f'"{c["text"]}" {c["citation"]}')
        
    coverage_partial = any(r.coverage == "partial" for r in rows)
    if coverage_partial:
        lead.append("Some change is not explained by disclosed volume/price data.")
        
    text = " ".join(lead)
    
    # Grounding check
    text, dropped = check_numeric_grounding(text, allowed, fallback_template="The numbers could not be fully grounded.")
    
    sources = [{"kind": "data", "object": "ssot", "ref": "v_fin_statement_as_reported"}]
    for c in chunks:
        sources.append({"kind": "ar", "ref": c["citation"], "text": c["text"]})
        
    # Visual
    if bridge:
        # M-BRIDGE -> waterfall
        visual = {
            "type": "chart", 
            "chart": {
                "kind": "waterfall", 
                "data": {
                    "columns": ["line_code", "impact"],
                    "rows": [{"line_code": "Start", "impact": bridge.start}] + 
                            [{"line_code": r.line_code, "impact": r.impact_on_pbt_inr_cr} for r in rows] +
                            [{"line_code": "End", "impact": bridge.end}]
                }
            }
        }
    else:
        visual = {
            "type": "table",
            "table": {
                "columns": ["Component", "Impact"],
                "rows": [{"Component": r.component, "Impact": r.impact_inr_cr} for r in rows]
            }
        }

    contract = {
        "turn_id": turn_id, 
        "language": language, 
        "persona": persona,
        "spoken_summary": "Here is the variance analysis.", 
        "display_text": text,
        "visual": visual,
        "insights": [],
        "sources": sources,
        "suggestions": [], 
        "access": {"status": "allowed"}, 
        "export_options": ["sheets", "pdf"],
        "status_events": ["Generated variance attribution and retrieved AR chunks"],
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        "contract_version": 2, 
        "query_spec": plan.spec.to_contract(),
    }
    
    return {"contract": contract, "meta": None}
