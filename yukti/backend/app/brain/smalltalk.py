"""Small talk and capability answers for turns the data planner does not handle (26-Oct).

Greetings ("Hi Yukti, how are you?"), "What can you do?", and other non-data turns used to fall through to the retired
legacy agent and show the generic error E-PLN-1234. This module answers them with one plain Gemini call: no tools, no
data access, English/Hindi/Hinglish only, and never any figures (so it cannot invent numbers). If the model is slow or
unavailable, a deterministic reply is used instead.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from app.config import DEFAULT_TEXT_MODEL, GCP_PROJECT, VERTEX_TEXT_LOCATION

logger = logging.getLogger("yukti.brain.smalltalk")

_HR_STARTERS = [
    "How many executives have been posted in Delhi for 5 years or more?",
    "Show headcount by discipline",
    "What is the transfer policy for station tenure?",
]
_FIN_STARTERS = [
    "Show ONGC's P&L statement for FY26",
    "Which fields were the most profitable in FY26?",
    "How are we tracking against our MoU targets this year?",
]
_CMD_STARTERS = [
    "How many executives have been posted in Delhi for 5 years or more?",
    "Which fields or assets were the most profitable and which made losses in FY26?",
    "How are we tracking against our MoU targets with MoPNG/DPE for this year?",
]


def starters_for(persona: str) -> List[str]:
    p = (persona or "").upper()
    if p == "CMD":
        return list(_CMD_STARTERS)
    if "FIN" in p:
        return list(_FIN_STARTERS)
    return list(_HR_STARTERS)


def _scope_for(persona: str) -> str:
    p = (persona or "").upper()
    if p == "CMD":
        return "HR and Finance across ONGC (people, postings, pay, P&L, balance sheet, field economics, MoU targets, policies)"
    if "FIN" in p:
        return "Finance (P&L, balance sheet, cash flow, field economics, MoU targets) and finance policies"
    return "HR (headcount, postings and transfers, tenure, leave, pay and benefits) and HR policies"


_SYSTEM = """You are Yukti, the voice-first HR & Finance agent for ONGC (Oil and Natural Gas Corporation Limited).
Reply to the user's message in 1-3 short, warm, professional sentences (Indian boardroom register).
Rules:
- Reply in the language named below ("Reply language"). Never any other language.
- Never state numbers, figures, names of employees, or facts about ONGC data. You have no data in this reply.
- For greetings: greet back briefly and offer help.
- For "what can you do" / help: say in one or two sentences what you can help with, using the scope given.
- If the message is a data or policy question you could not answer, say you couldn't fetch that just now and ask the
  user to rephrase it more specifically (e.g. with a year, location or metric). Do not guess an answer.
- If the message looks cut off or incomplete (e.g. "Can you tell"), ask the user to finish the question.
- If the message is unclear or seems to be noise, ask the user to repeat.
Return plain text only."""

_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(vertexai=True, project=GCP_PROJECT, location=VERTEX_TEXT_LOCATION)
    return _client


_DIGITS = re.compile(r"\d")


def _fallback_text(query: str, persona: str, language: str) -> str:
    q = (query or "").lower()
    if language == "hi":
        if re.search(r"(kya kar|madad|help)", q):
            return f"Main {_scope_for(persona)} se jude sawalon mein aapki madad kar sakti hoon. Aap neeche diye sawal se shuru kar sakte hain."
        return "Namaste! Main Yukti hoon. Bataiye, main aapki kya madad kar sakti hoon?"
    if re.search(r"(what can you do|help|capabilit|what do you do)", q):
        return f"I can answer questions on {_scope_for(persona)}, show the right table or chart, and draft notes. Try one of the questions below."
    if re.search(r"\b(hi|hello|hey|namaste|good (morning|afternoon|evening)|how are you)\b", q):
        return "Hello! I'm doing well, thank you. How can I help you today?"
    return "Sorry, I couldn't work that out. Could you rephrase it with a little more detail, such as a year, location or metric?"


async def smalltalk_reply(query: str, persona: str, language: str) -> str:
    reply_lang = {"hi": "Hindi (Devanagari)", "hi-en": "Hinglish (Roman script)"}.get(language, "Indian English")
    prompt = (
        f"{_SYSTEM}\n\nUser role: {persona}. You can help with: {_scope_for(persona)}.\n"
        f"Reply language: {reply_lang}.\nUser message: {query}"
    )
    try:
        cfg = types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=160,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
        resp = await asyncio.wait_for(
            _get_client().aio.models.generate_content(model=DEFAULT_TEXT_MODEL, contents=prompt, config=cfg),
            timeout=6,
        )
        text = (resp.text or "").strip()
        # guard: this reply has no data, so it must not carry figures
        if text and not _DIGITS.search(text):
            return text
        logger.info("smalltalk: model reply rejected (empty or contained digits); using fallback")
    except Exception as e:  # noqa: BLE001 - any failure falls back to a deterministic reply
        logger.warning(f"smalltalk: model call failed ({type(e).__name__}); using fallback")
    return _fallback_text(query, persona, language)


async def build_smalltalk_contract(
    query: str, persona: str, turn_id: str, language: str, t0: float
) -> Dict[str, Any]:
    text = await smalltalk_reply(query, persona, language)
    return {
        "turn_id": turn_id,
        "language": language,
        "persona": persona,
        "spoken_summary": text,
        "display_text": text,
        "visual": {"type": "none", "mode": "replace"},
        "insights": [],
        "sources": [],
        "suggestions": starters_for(persona),
        "access": {"status": "allowed"},
        "export_options": [],
        "status_events": ["Answered conversationally (no data used)"],
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
    }
