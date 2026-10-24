from app.agents.types import AgentContext, AgentResult

async def run(ctx: AgentContext, inputs: dict) -> AgentResult:
    # Skeleton reference logic (P2F logic would go here)
    return {
        "visual": {"type": "fin_diagnostics", "mode": "replace"},
        "access": {"status": "allowed"}
    }
