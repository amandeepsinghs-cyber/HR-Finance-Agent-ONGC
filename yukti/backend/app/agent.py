"""Google ADK Agent definition for Yukti AI.
Implements the Yukti persona: brief 2–4 sentence spoken answers,
mirroring user language (en/hi/hi-en), Indian number system, citing sources,
and strictly answering from BigQuery and Vertex AI Search.
"""

import asyncio
import logging
import os
import re
import uuid
from typing import Any, Dict, List, Optional
from google.adk.agents import Agent
from google.genai import types

from app.config import DEFAULT_LIVE_MODEL, DEFAULT_TEXT_MODEL, DEFAULT_VOICE, FALLBACK_LIVE_MODEL
from app.tools.certified_query import run_certified_query as execute_certified_query
from app.tools.draft_document import DocumentDraftingEngine
from app.tools.export_tool import DocumentExporter
from app.tools.policy_search import PolicySearchEngine
from app.tools.query_data import query_data as execute_query_data
from app.tools.semantic_layer import SEMANTIC_LAYER_PROMPT
from app.tools.what_if import run_what_if_simulation

logger = logging.getLogger("yukti.agent")

# Official Yukti System Instructions per approved UX Spec §1, §4, §8, §9, §14
YUKTI_SYSTEM_INSTRUCTION = f"""You are "Yukti", the authoritative voice-first AI agent for ONGC's Chairman & Managing Director (CMD) and executive leadership.
You deliver instant, grounded intelligence across Human Resources and Finance.

CORE OPERATIONAL BEHAVIORS:
1. Executive Voice & Persona (UX Spec §9):
   - Deliver brief, punchy spoken summaries (STRICTLY 2 to 3 sentences).
   - NEVER enumerate all rows or all 9 executive grades verbally. State the overall total count/amount and highlight at most the top 1 or 2 items. Direct the presenter's attention to the interactive canvas chart.
   - Use the EXACT totals and counts provided in the tool's `deterministic_summary`. Never extrapolate or hallucinate numbers from preview rows.
   - Use the Indian numbering system naturally (Lakh, Crore, e.g. "₹6.50 Crore", "1.32 Lakh Crore", "419 executives").
   - Never invent numbers. If data is not available or a query returns 0 rows, state plainly: "Data not available: here is the closest verified information."

2. SPOKEN CITATION RULES (USER DECISION):
   - Spoken answers MUST NEVER mention dataset names, table names, documents, or clause numbers by default. Deliver pure business intelligence.
   - Never say "as verified in hrfin_gold", "according to table v_continuous_stay", or "Clause 3.0".
   - Sources appear visually ONLY at the bottom of the canvas.
   - Exception: for policy questions, you may mention the policy name naturally ("Under the transfer policy, ...") but NOT clause numbers unless asked.
   - SOURCE INQUIRIES: Only when the user explicitly asks ("what's the source?", "where is this from?", "kiska data hai?"), speak the source in plain business language (e.g. "This comes from the HR posting records (demo data) as of today, and the JRTP transfer policy (illustrative text)."). Never speak database table or view names even then.

3. MANDATORY TOOL USAGE FOR ONGC DATA & METRICS:
   - You MUST call a tool (`run_certified_query`, `query_data`, `search_policy`, `what_if`, or `draft_document`) for EVERY user question inquiring about ONGC data, metrics, headcount, policies, finances, or operations.
   - When the user inquiry matches a certified metric or question (e.g. C1 Delhi stay, C6 loss-making fields, C12 lifting cost, vacancies, capex), call `run_certified_query(query_id, params)` to execute the verified certified template, supplying parameter overrides as requested (e.g. wc_id, fiscal_year, min_stay_months).
   - Direct model reasoning without a tool call is STRICTLY FORBIDDEN for any question asking for numbers, metrics, or factual statements.
   - Direct text responses without a tool call are permitted ONLY for greetings (e.g. "hello", "good morning"), conversational pleasantries, and meta questions.
   - TOOL SELECTION RULES:
     * Structured data & metrics (headcount, tenure, stay duration, field P&L, lifting cost, vacancies, capex, CAG paras, financial ratios): call `query_data`.
     * Policies, guidelines, rules, entitlements (leave, maternity, paternity, transfer rules, CDA rules, retention guidelines): call `search_policy`. Policies are in Vertex AI Search, NOT in BigQuery SQL tables. Do NOT attempt to SELECT from `hrfin_docs`.
     * What-if simulations (Brent price shock, recruitment freeze, relocation budget): call `what_if`.
     * Drafting official letters or Parliament replies: call `draft_document`.

3. SQL Generation & Repair Cap:
   - If a SQL query fails syntax validation, attempt at most ONE self-correction. If it fails a second time, report that data is not available.

4. Multilingual & Script Mirroring:
   - Seamlessly converse in English, Hindi, and mixed Hindi-English (Hinglish).
   - Reply in the language and register of the question.

3. Role-Based Access Control:
   - For restricted personas (e.g. E2 HR Officer Pooja Verma or E3 Finance Officer Rajesh Kulkarni), strictly refuse access to confidential personal data (CDA Rule 5.0) or unpromulgated transfer proposals (JRTP Clause 11.0).
   - Deliver polite, brief refusal justifications citing the governing rule, and present authorized public aggregates or policy guidelines.

4. Opening Greeting:
   - When a session initiates, greet the executive:
     "Hello, I am Yukti, your HR and Finance agent. Please tell me how I can help."
     (In Hindi: "नमस्ते, मैं युक्ति हूँ, आपकी एचआर और वित्त सलाहकार। कृपया बताइए मैं आपकी क्या सहायता कर सकती हूँ।")

{SEMANTIC_LAYER_PROMPT}
"""

_POLICY_ENGINE = PolicySearchEngine()
_DRAFT_ENGINE = DocumentDraftingEngine()
_EXPORT_ENGINE = DocumentExporter()


async def query_data(sql_query: str, title: Optional[str] = None) -> Dict[str, Any]:
    """Executes a SELECT query on BigQuery datasets hrfin_gold or hrfin_silver.

    Always follow the 5 Query-Craft rules and dataset allow-list.
    """
    return await asyncio.to_thread(execute_query_data, sql_query=sql_query, title=title)


async def run_certified_query(
    query_id: str,
    params: Optional[Dict[str, Any]] = None,
    wc_id: Optional[str] = None,
    fiscal_year: Optional[str] = None,
    min_stay_months: Optional[int] = None,
    min_grade: Optional[str] = None,
    field_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Executes a certified parameterized query template from the verified query library.
    ALWAYS prefer calling `run_certified_query` first before `query_data` for standard questions:
    - 'C1': Executives with >= N months continuous stay at a work centre (wc_id='WC-DEL'|'WC-MUM'|'WC-DDN'|'WC-AHM'|'WC-MEH'|'WC-ASM'|'WC-TRI', min_stay_months=60, min_grade='E5')
    - 'C6': Field profitability and loss-making fields (fiscal_year='FY26'|'FY25')
    - 'C10': MoU performance scorecard vs targets
    - 'C11': Assets that added headcount vs production growth
    - 'C12': Lifting cost per BOE across assets (fiscal_year='FY26')
    - 'F6': Trade receivables ageing by customer
    - 'H10': Annual transfer proposal roster
    - 'X7': North-East vacancies category-wise
    """
    merged: Dict[str, Any] = dict(params or {})
    if wc_id:
        merged["wc_id"] = wc_id
    if fiscal_year:
        merged["fiscal_year"] = fiscal_year
    if min_stay_months is not None:
        merged["min_stay_months"] = min_stay_months
    if min_grade:
        merged["min_grade"] = min_grade
    if field_id:
        merged["field_id"] = field_id
    return await asyncio.to_thread(execute_certified_query, query_id=query_id, params=merged or None)


async def search_policy(query: str) -> Dict[str, Any]:
    """Searches official ONGC policy manuals and rulebooks for matching clauses."""
    return await asyncio.to_thread(_POLICY_ENGINE.search, query=query)


async def what_if(
    scenario: str,
    brent_price: Optional[float] = 60.0,
    freeze_months: Optional[int] = 24,
    relocated_officers: Optional[int] = 200,
    cta_lakh: Optional[float] = 3.25,
) -> Dict[str, Any]:
    """Runs a live parameterized what-if simulation on BigQuery:

    - scenario='brent_price': brent_price=$60.0 (or custom price)
    - scenario='recruitment_freeze': freeze_months=24
    - scenario='relocation': relocated_officers=200, cta_lakh=3.25
    - scenario='saed': windfall tax withdrawal
    """
    return await asyncio.to_thread(
        run_what_if_simulation,
        scenario=scenario,
        brent_price=brent_price,
        freeze_months=freeze_months,
        relocated_officers=relocated_officers,
        cta_lakh=cta_lakh,
    )


async def draft_document(
    doc_type: str,
    topic: str,
    instruction: Optional[str] = None,
    version: int = 1,
) -> Dict[str, Any]:
    """Drafts or revises an official ONGC Board Note, Parliament Reply, AGT Transfer Proposal, or Letter.

    Supports instruction='make it shorter', 'add Brent $60 scenario', 'translate to Hindi'.
    """
    return await asyncio.to_thread(
        _DRAFT_ENGINE.draft,
        doc_type=doc_type,
        query=topic,
        version=version,
        instruction=instruction,
    )


def _export_document_sync(format: str, title: str, content: str) -> Dict[str, Any]:
    fmt = format.lower()
    # H1.3a: the title comes from the model — never use it as a raw path (DocumentExporter.safe_path also guards)
    title = re.sub(r"[^A-Za-z0-9_\-]", "_", str(title or "Yukti_Export"))[:80] or "Yukti_Export"
    export_id = f"exp_{uuid.uuid4().hex}"  # minted id: no cross-user overwrite, no server path back to the model
    if "word" in fmt or "docx" in fmt:
        _EXPORT_ENGINE.export_word(markdown_text=content, filename=f"{export_id}.docx")
        return {"status": "success", "export_id": export_id, "filename": f"{title}.docx", "format": "docx"}
    elif "pdf" in fmt:
        _EXPORT_ENGINE.export_pdf(markdown_text=content, filename=f"{export_id}.pdf")
        return {"status": "success", "export_id": export_id, "filename": f"{title}.pdf", "format": "pdf"}
    elif "doc" in fmt:
        res = _EXPORT_ENGINE.export_google_docs(title=title, markdown_text=content, file_id=export_id)
        return {"status": "success", "export_id": export_id, "filename": f"{title}.docx", "format": "docs", "url": res.get("url")}
    return {"status": "success", "format": fmt}


async def export_document(format: str, title: str, content: str) -> Dict[str, Any]:
    """Exports documents or tabular statements to Word (.docx), Excel (.xlsx), PDF, or Google Docs/Sheets."""
    return await asyncio.to_thread(_export_document_sync, format, title, content)


def create_yukti_agent(
    model_name: Optional[str] = None,
    instruction_override: Optional[str] = None,
) -> Agent:
    """Instantiates the Google ADK Agent for Yukti AI with minimal thinking overhead."""
    active_model = model_name or os.getenv("YUKTI_TEXT_MODEL", DEFAULT_TEXT_MODEL)
    instruction = instruction_override or YUKTI_SYSTEM_INSTRUCTION

    # Optimize thinking budget for text models only (live audio models do not customize thinking level)
    if "live" not in active_model.lower():
        if "3." in active_model or "3-" in active_model:
            gen_cfg = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="low")
            )
        else:
            gen_cfg = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            )
    else:
        gen_cfg = None

    return Agent(
        name="yukti_ai_agent",
        model=active_model,
        instruction=instruction,
        generate_content_config=gen_cfg,
        tools=[
            run_certified_query,
            query_data,
            search_policy,
            what_if,
            draft_document,
            export_document,
        ],
    )
