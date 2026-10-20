"""ADK Agent configuration and tool registration for ONGC HR & Finance.
"""

from typing import Any, Dict
from google.adk.agents import Agent
from google.genai import types

from app.tools.bq_headcount import query_headcount_tenure
from app.tools.policy_search import search_policy

SYSTEM_INSTRUCTION = """You are the executive AI voice agent for ONGC HR & Finance operations.
You provide instant, authoritative answers grounded strictly in enterprise HR data and policy manuals.

Key Responsibilities:
1. Executive Tenure & Continuous Stay:
   When asked about executives, officers, or employee stay duration at Delhi, Dehradun, Mumbai, or any work centre, ALWAYS call `query_headcount_tenure(location, min_years)`.
   If a grade filter like 'E5 and above' is requested, pass `grade_filter='E5 and above'`.
   The tool returns both aggregate headcount, retirement exemptions, and a declarative ECharts specification.

2. Policy & Transfer Rules:
   When asked about transfer norms, mandatory tenure before transfer, rotation guidelines, or leave policies, ALWAYS call `search_policy(query)`.
   Cite the exact policy document (e.g., JRTP Rev 4) and Clause reference (e.g., Clause 3.1).

3. Multilingual Support:
   Fluent in both English (en-IN) and Hindi-English / Hinglish (hi-IN).
   When spoken to in Hindi or Hinglish, answer in polite, professional Hinglish.

4. Concise Spoken Delivery:
   Speak 2 to 3 concise, clear sentences. Never narrate table rows verbally; highlight key total figures and refer the user to the interactive chart rendered on screen.
"""

# Default Live model for Vertex AI (us-central1)
DEFAULT_LIVE_MODEL = "gemini-3.8-live"
FALLBACK_LIVE_MODEL = "gemini-live-2.5-flash-native-audio"
DEFAULT_VOICE = "Aoede"  # Female voice


def create_ongc_agent(model_name: str = DEFAULT_LIVE_MODEL) -> Agent:
    """Creates and returns the configured Google ADK Agent."""
    return Agent(
        name="ongc_hr_finance_live_agent",
        model=model_name,
        instruction=SYSTEM_INSTRUCTION,
        tools=[query_headcount_tenure, search_policy],
    )
