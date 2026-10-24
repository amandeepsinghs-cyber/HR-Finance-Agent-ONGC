"""P3.6b — Voice confirm/cancel/edit and job-completion announcement tests (SPEC-03 AC-04, AC-08)."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

import pytest

from app.intents.confirm import (
    detect_confirm_intent,
    extract_voice_edits,
    resolve_pending_proposal_async,
)
from app.jobs.executor import get_executor
from app.jobs.store import reset_store_for_tests
from app.live_session import LiveSessionManager
from app.session_memory import get_session_manager


class FakeWebSocket:
    def __init__(self) -> None:
        self.sent: List[Dict[str, Any]] = []
        self.inbound_q: asyncio.Queue = asyncio.Queue()

    async def send_text(self, text: str) -> None:
        self.sent.append(json.loads(text))

    async def receive(self) -> Dict[str, Any]:
        return await self.inbound_q.get()


@pytest.fixture(autouse=True)
def _clean_jobs_and_sessions():
    reset_store_for_tests()
    sm = get_session_manager()
    sm.sessions.clear()
    executor = get_executor()
    executor.store = reset_store_for_tests() or executor.store
    from app.jobs.store import get_job_store
    executor.store = get_job_store()
    executor.step_delay_sec = 0.005
    yield


def test_spec03_regex_table_en_hinglish_devanagari():
    """SPEC-03 §6.2: Confirm, Cancel, and Edit-by-voice regex table across EN, Hinglish, and Devanagari."""
    for confirm_phrase in [
        "yes",
        "yeah, go ahead",
        "yep",
        "sure",
        "ok",
        "okay",
        "go ahead",
        "do it",
        "run",
        "run it",
        "please run",
        "haan",
        "haan ji",
        "ha, chalao",
        "chalao",
        "kar do",
        "chala do",
        "हाँ",
        "चलाओ",
    ]:
        assert detect_confirm_intent(confirm_phrase) == "confirm", f"Failed on {confirm_phrase!r}"

    for cancel_phrase in [
        "no",
        "nope",
        "cancel",
        "stop",
        "don't",
        "dont",
        "mat karo",
        "nahi",
        "रद्द",
        "नहीं",
    ]:
        assert detect_confirm_intent(cancel_phrase) == "cancel", f"Failed on {cancel_phrase!r}"

    # Edit by voice (SPEC-03 §6.2)
    assert detect_confirm_intent("wacc to 11.5%") == "edit"
    assert extract_voice_edits("set discount rate = 11.25% and terminal growth of 3.5% with brent at $78") == {
        "wacc_pct": 11.25,
        "terminal_g_pct": 3.5,
        "brent_usd": 78.0,
    }

    # Unrelated question stays None
    assert detect_confirm_intent("what is ONGC revenue in FY26?") is None


@pytest.mark.asyncio
async def test_voice_confirm_starts_job_and_announces_verbatim_zero_duplicate_bubbles():
    """SPEC-03 AC-04 & AC-08:
    WS script: proposal pending -> user says 'haan, chalao' -> Echo 'You said: haan, chalao' ->
    job runs -> job_update succeeded -> announcement text == result.spoken_summary with speak_id=job:<id>:1 ->
    exactly 1 result contract bubble and 0 duplicate agent_transcript bubbles.
    """
    ws = FakeWebSocket()
    session_id = "sess_voice_p36b"
    mgr = LiveSessionManager(websocket=ws, session_id=session_id, persona="CMD", language="en")

    # Seed a pending DCF proposal in the session (as emitted by "run a DCF")
    pa_id = "pa_dcf_001"
    mgr.session_state.pending_actions[pa_id] = {
        "id": pa_id,
        "agent": "dcf_agent",
        "agent_version": "dcf-v1.0.0",
        "summary": "Run 10-year standalone + SOTP DCF valuation for ONGC.",
        "est_seconds": 8,
        "requires_role": ["CMD", "DIR_FIN"],
        "inputs": {"wacc_pct": 10.5, "terminal_g_pct": 3.0, "brent_usd": 75.0},
        "editable_inputs": [
            {"key": "wacc_pct", "label": "WACC (%)", "type": "percent", "value": 10.5, "min": 6, "max": 16, "step": 0.25},
            {"key": "terminal_g_pct", "label": "Terminal g (%)", "type": "percent", "value": 3.0, "min": 0, "max": 6, "step": 0.25},
            {"key": "brent_usd", "label": "Brent (USD/bbl)", "type": "number", "value": 75.0, "min": 40, "max": 120, "step": 1},
        ],
    }

    loop_task = asyncio.create_task(mgr._run_fallback_loop())
    try:
        # User confirms by voice/text in Hinglish: "haan, chalao"
        await mgr.inbound.put({"text": json.dumps({"type": "text", "text": "haan, chalao"})})

        # Wait for background job to finish and push job_update + speak turn_complete
        for _ in range(100):
            await asyncio.sleep(0.02)
            speak_turns = [
                m for m in ws.sent
                if m.get("type") == "turn_complete" and str(m.get("speak_id") or "").startswith("job:")
            ]
            if speak_turns:
                break

        # 1. Verify Echo "You said: haan, chalao"
        user_transcripts = [m for m in ws.sent if m.get("type") == "user_transcript"]
        assert any(m.get("text") == "You said: haan, chalao" for m in user_transcripts)

        # 2. Verify job started and succeeded
        job_updates = [m["job"] for m in ws.sent if m.get("type") == "job_update" and "job" in m]
        succeeded_jobs = [j for j in job_updates if j.get("status") == "succeeded"]
        assert len(succeeded_jobs) >= 1
        job_id = succeeded_jobs[-1]["id"]

        # 3. Verify result contract emitted exactly once and zero duplicate agent_transcript bubbles
        result_contracts = [
            m["contract"]
            for m in ws.sent
            if m.get("type") == "contract" and m["contract"].get("turn_id") == f"job:{job_id}"
        ]
        assert len(result_contracts) == 1
        result_contract = result_contracts[0]

        agent_transcripts = [m for m in ws.sent if m.get("type") == "agent_transcript"]
        assert len(agent_transcripts) == 0, f"Expected 0 duplicate agent_transcript bubbles, got {agent_transcripts}"

        # 4. SPEC-03 AC-08: announcement text == result.spoken_summary with speak_id == job:<id>:1
        speak_turns = [
            m for m in ws.sent
            if m.get("type") == "turn_complete" and m.get("speak_id") == f"job:{job_id}:1"
        ]
        assert len(speak_turns) == 1
        assert speak_turns[0]["full_text"] == result_contract["spoken_summary"]
    finally:
        await mgr.inbound.put(None)
        mgr.active = False
        loop_task.cancel()
        with pytest.raises((asyncio.CancelledError, Exception)):
            await loop_task


@pytest.mark.asyncio
async def test_two_pending_proposals_disambiguation_and_queuing_while_user_speaking():
    """SPEC-03 AC-04 & §9:
    - With two pending proposals, 'yes, run it' asks 'Run the DCF or the email send?'
    - When user is speaking during job completion, announcement is queued until user turn finishes.
    """
    ws = FakeWebSocket()
    session_id = "sess_voice_two_pa"
    mgr = LiveSessionManager(websocket=ws, session_id=session_id, persona="CMD", language="en")

    mgr.session_state.pending_actions["pa_1"] = {
        "id": "pa_1",
        "agent": "dcf_agent",
        "summary": "Run DCF",
        "requires_role": ["CMD", "DIR_FIN"],
    }
    mgr.session_state.pending_actions["pa_2"] = {
        "id": "pa_2",
        "agent": "hr_transfer_agent",
        "summary": "Send email to Director HR",
        "requires_role": ["CMD", "DIR_HR"],
    }

    res = await resolve_pending_proposal_async("yes, run it", mgr.session_state)
    assert res is not None
    assert res["action"] == "clarify_multiple"
    assert res["echo"] == "You said: yes, run it"
    assert res["contract"]["spoken_summary"] == "Run the DCF or the email send?"

    # Now test queuing when user is speaking while a job finishes
    mgr._user_is_speaking = True
    fake_job = {
        "id": "job_queued_123",
        "agent": "dcf_agent",
        "status": "succeeded",
        "progress": 1.0,
        "result": {
            "contract_version": 3,
            "turn_id": "job:job_queued_123",
            "spoken_summary": "The DCF valuation is ready. Intrinsic value is ₹312.40 per share. This is an illustrative valuation, not investment advice.",
            "display_text": "The DCF valuation is ready.",
            "visual": {"type": "dcf_model", "mode": "replace"},
            "access": {"status": "allowed"},
        },
    }
    await mgr.handle_job_update(fake_job)
    # While user is speaking, speak is queued, not yet in inbound queue
    assert len(mgr._queued_job_speaks) == 1
    assert mgr.inbound.empty()

    # User finishes speaking -> flush queued job speaks
    mgr._user_is_speaking = False
    await mgr._flush_queued_job_speaks()
    assert len(mgr._queued_job_speaks) == 0
    queued_msg = json.loads((await mgr.inbound.get())["text"])
    assert queued_msg["type"] == "speak"
    assert queued_msg["speak_id"] == "job:job_queued_123:1"
    assert queued_msg["text"] == fake_job["result"]["spoken_summary"]
