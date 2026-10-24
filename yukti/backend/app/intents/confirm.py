from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# SPEC-03 §6.2 Voice and text confirmation (deterministic, no LLM)
CONFIRM_RE = re.compile(
    r"^\s*(yes|yeah|yep|sure|ok(ay)?|go ahead|do it|run( it)?|please run|haan ji|haan|ha|chalao|kar do|chala do|हाँ|चलाओ|proceed)(?=$|[\s,.!?;:])",
    re.IGNORECASE,
)

CANCEL_RE = re.compile(
    r"(?:^\s*|\b)(no|nope|cancel|stop|don'?t|mat karo|nahi|रद्द|नहीं)(?=$|[\s,.!?;:])",
    re.IGNORECASE,
)

WACC_EDIT_RE = re.compile(
    r"\b(?:wacc|discount rate)\s*(?:of|=|to|is|at)?\s*(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)

GROWTH_EDIT_RE = re.compile(
    r"\b(?:terminal growth|growth|g)\s*(?:of|=|to|is|at)?\s*(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)

BRENT_EDIT_RE = re.compile(
    r"\bbrent\s*(?:at|=|to|of|is)?\s*\$?\s*(\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)

GENERIC_EDIT_RE = re.compile(
    r"\b(edit|change|modify|update)\b",
    re.IGNORECASE,
)

QUESTION_LEAD_RE = re.compile(
    r"^\s*(what|why|how|which|who|when|where|show|tell)\b",
    re.IGNORECASE,
)


def extract_voice_edits(text: str) -> Dict[str, float]:
    """Extract parameter overrides spoken or typed by the user per SPEC-03 §6.2."""
    if not text:
        return {}
    edits: Dict[str, float] = {}
    m_wacc = WACC_EDIT_RE.search(text)
    if m_wacc:
        edits["wacc_pct"] = float(m_wacc.group(1))
    m_g = GROWTH_EDIT_RE.search(text)
    if m_g:
        edits["terminal_g_pct"] = float(m_g.group(1))
    m_brent = BRENT_EDIT_RE.search(text)
    if m_brent:
        edits["brent_usd"] = float(m_brent.group(1))
    return edits


def detect_confirm_intent(text: str) -> Optional[str]:
    """Classify an utterance against SPEC-03 §6.2 into 'confirm', 'cancel', 'edit', or None."""
    cleaned = (text or "").strip()
    if not cleaned:
        return None

    if CANCEL_RE.search(cleaned):
        return "cancel"

    edits = extract_voice_edits(cleaned)
    if edits:
        return "edit"

    if not QUESTION_LEAD_RE.search(cleaned) and GENERIC_EDIT_RE.search(cleaned):
        return "edit"

    if CONFIRM_RE.search(cleaned):
        return "confirm"

    return None


def _is_expired(expires_at: Optional[str]) -> bool:
    if not expires_at:
        return False
    try:
        dt = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt <= datetime.now(timezone.utc)
    except ValueError:
        return False


def get_active_pending_actions(session_state: Any) -> Dict[str, Dict[str, Any]]:
    raw = getattr(session_state, "pending_actions", None) or {}
    active: Dict[str, Dict[str, Any]] = {}
    expired_ids = []
    for aid, pa in list(raw.items()):
        if isinstance(pa, dict) and _is_expired(pa.get("expires_at")):
            expired_ids.append(aid)
        elif isinstance(pa, dict) and not pa.get("disabled"):
            active[aid] = pa
    for aid in expired_ids:
        raw.pop(aid, None)
    return active


async def resolve_pending_proposal_async(
    text: str,
    session_state: Any,
) -> Optional[Dict[str, Any]]:
    """Deterministically resolve voice/text confirmation, cancellation, or edit against session_state.pending_actions."""
    if session_state is None:
        return None
    active = get_active_pending_actions(session_state)
    if not active:
        return None

    intent = detect_confirm_intent(text)
    edits = extract_voice_edits(text)
    if intent is None and not edits:
        return None

    utterance_clean = (text or "").strip()
    echo_text = f"You said: {utterance_clean}"
    lang = getattr(session_state, "language", "en") or "en"
    persona = getattr(session_state, "persona", "CMD") or "CMD"

    # SPEC-03 §6.2: if two non-expired proposals exist, ask which one to run
    if len(active) >= 2:
        msg = "Run the DCF or the email send?"
        return {
            "action": "clarify_multiple",
            "echo": echo_text,
            "contract": {
                "contract_version": 3,
                "turn_id": f"turn-clarify-pa-{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                "language": lang,
                "persona": persona,
                "spoken_summary": msg,
                "display_text": msg,
                "visual": {"type": "none", "mode": "replace"},
                "access": {"status": "allowed"},
            },
        }

    action_id, pa = next(iter(active.items()))

    if intent == "cancel":
        session_state.pending_actions.pop(action_id, None)
        msg = "Cancelled. No agent was run."
        return {
            "action": "cancel",
            "action_id": action_id,
            "echo": echo_text,
            "contract": {
                "contract_version": 3,
                "turn_id": f"turn-cancel-{action_id}",
                "language": lang,
                "persona": persona,
                "spoken_summary": msg,
                "display_text": msg,
                "visual": {"type": "none", "mode": "replace"},
                "access": {"status": "allowed"},
            },
        }

    if intent == "edit":
        updated_pa = dict(pa)
        inputs = dict(updated_pa.get("inputs") or {})
        editable = [dict(item) for item in (updated_pa.get("editable_inputs") or [])]
        changed_parts = []
        for k, v in edits.items():
            inputs[k] = v
            for item in editable:
                if item.get("key") == k:
                    item["value"] = v
                    item["edited_by_user"] = True
            label = "WACC" if k == "wacc_pct" else ("terminal g" if k == "terminal_g_pct" else "Brent")
            unit = "%" if "pct" in k else " USD/bbl"
            changed_parts.append(f"{label} = {v}{unit}")
        updated_pa["inputs"] = inputs
        updated_pa["editable_inputs"] = editable
        change_str = ", ".join(changed_parts) if changed_parts else "updated assumptions"
        summary = f"Updated assumptions ({change_str}). Shall I run the {updated_pa.get('agent', 'agent')} with these values?"
        updated_pa["summary"] = summary
        session_state.pending_actions[action_id] = updated_pa
        return {
            "action": "edit",
            "action_id": action_id,
            "overrides": edits,
            "echo": echo_text,
            "contract": {
                "contract_version": 3,
                "turn_id": f"turn-edit-{action_id}",
                "language": lang,
                "persona": persona,
                "spoken_summary": summary,
                "display_text": summary,
                "visual": {"type": "none", "mode": "replace"},
                "proposed_action": updated_pa,
                "access": {"status": "allowed"},
            },
        }

    # intent == "confirm"
    from app.jobs.executor import get_executor

    executor = get_executor()
    session_state.pending_actions.pop(action_id, None)
    job = await executor.submit_job(pa, session_state.session_id)
    started_msg = f"Starting {pa.get('agent', 'dcf_agent')}. I will announce the result as soon as it finishes."
    return {
        "action": "confirm",
        "action_id": action_id,
        "job": job,
        "echo": echo_text,
        "contract": {
            "contract_version": 3,
            "turn_id": f"turn-job-start-{job['id']}",
            "language": lang,
            "persona": persona,
            "spoken_summary": started_msg,
            "display_text": started_msg,
            "visual": {"type": "none", "mode": "replace"},
            "job": job,
            "access": {"status": "allowed"},
        },
    }
