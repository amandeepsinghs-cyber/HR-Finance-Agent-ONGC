"""P0.10 (BUG-17/18): half-duplex mic gate, deliberate barge-in and speak_id gating in the Live session.

Offline: a fake Gemini Live session replaces `client.aio.live.connect`; we drive the browser side through
`LiveSessionManager.inbound` and the model side through a queue of scripted server messages.
"""

import array
import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import live_session as ls  # noqa: E402
from app.live_session import LiveSessionManager  # noqa: E402


def _pcm(peak: int = 3000, n: int = 1600) -> bytes:
    return array.array("h", [peak if i % 2 else -peak for i in range(n)]).tobytes()


class FakeLive:
    def __init__(self):
        self.audio_in = []          # mic frames forwarded to Gemini
        self.client_content = []
        self.q: asyncio.Queue = asyncio.Queue()

    async def send_realtime_input(self, audio=None, audio_stream_end=None, **_):
        if audio is not None:
            self.audio_in.append(audio)

    async def send_client_content(self, turns=None, turn_complete=None):
        self.client_content.append(turns)

    async def send_tool_response(self, **_):
        pass

    async def receive(self):
        while True:
            item = await self.q.get()
            if item is None:
                return
            yield item


def sc(**kw):
    base = dict(interrupted=False, input_transcription=None, output_transcription=None, model_turn=None,
                turn_complete=False)
    base.update(kw)
    return NS(session_resumption_update=None, go_away=None, tool_call=None, server_content=NS(**base))


def audio_turn(nbytes=4800):
    return sc(model_turn=NS(parts=[NS(text=None, inline_data=NS(data=b"\x01\x00" * (nbytes // 2)))]))


class Harness:
    def __init__(self):
        self.sent = []

        class WS:
            async def send_text(s, text):  # noqa: N805
                self.sent.append(json.loads(text))

        self.mgr = LiveSessionManager(WS(), session_id=f"p010-{id(self)}")
        self.live = FakeLive()
        self.task = None

    async def start(self):
        self.task = asyncio.create_task(self.mgr._run_bidi_stream(self.live))
        await asyncio.sleep(0.01)

    async def browser(self, **msg):
        if "bytes" in msg:
            await self.mgr.inbound.put({"bytes": msg["bytes"]})
        else:
            await self.mgr.inbound.put({"text": json.dumps(msg)})
        await asyncio.sleep(0.02)

    async def server(self, item):
        await self.live.q.put(item)
        await asyncio.sleep(0.02)

    async def stop(self):
        await self.mgr.inbound.put(ls._CLOSED)
        await asyncio.wait_for(self.task, timeout=2)

    def of_type(self, t):
        return [m for m in self.sent if m.get("type") == t]


def test_gate_logic_states():
    h = Harness()
    m = h.mgr
    assert m._mic_gate_open() is True                 # idle
    m._generating = True
    assert m._mic_gate_open() is False                # Yukti generating
    m._barge_in_open = True
    assert m._mic_gate_open() is True                 # deliberate barge-in
    m._barge_in_open, m._generating = False, False
    m._is_speak_only = True
    assert m._mic_gate_open() is False                # speak turn
    m._is_speak_only = False
    m._playback_until = ls.time.perf_counter() + 0.2
    assert m._mic_gate_open() is False                # browser still playing (estimate)
    m._playback_until = ls.time.perf_counter() - ls.PLAYBACK_TAIL_S - 0.01
    assert m._mic_gate_open() is True                 # playback + 300 ms tail over


def test_live_config_lowers_start_of_speech_sensitivity():
    from google.genai import types
    cfg = Harness().mgr._build_live_config(None)
    aad = cfg.realtime_input_config.automatic_activity_detection
    assert aad.start_of_speech_sensitivity == types.StartSensitivity.START_SENSITIVITY_LOW


@pytest.mark.asyncio
async def test_mic_frames_dropped_while_generating_and_during_playback_tail():
    h = Harness()
    await h.start()
    await h.server(audio_turn(nbytes=4800))           # 0.1 s of audio -> generating + playback estimate
    await h.browser(bytes=_pcm())                     # echo while Yukti speaks
    assert h.live.audio_in == [] and h.mgr._mic_frames_dropped == 1
    await h.server(sc(turn_complete=True))            # generation done, but the browser is still playing
    await h.browser(bytes=_pcm())
    assert h.live.audio_in == [], "frame inside playback + 300 ms tail must be dropped"
    await asyncio.sleep(0.1 + ls.PLAYBACK_TAIL_S + 0.05)
    await h.browser(bytes=_pcm())
    assert len(h.live.audio_in) == 1, "after playback + tail the mic is live again"
    await h.stop()


@pytest.mark.asyncio
async def test_deliberate_interrupt_reopens_gate_but_keeps_speak_only_until_its_turn_complete():
    h = Harness()
    await h.start()
    await h.browser(type="speak", text="FY24 total assets are four lakh crore.", speak_id="S1")
    assert h.mgr._is_speak_only and h.mgr._speak_id == "S1"
    await h.server(audio_turn())
    await h.browser(bytes=_pcm())
    assert h.live.audio_in == []                      # speak turn: gated
    await h.browser(type="interrupt")                 # user taps Stop / orb / Space
    assert h.mgr._is_speak_only is True and h.mgr._speak_id == "S1", "interrupt must not clear speak-only"
    assert h.mgr._barge_in_open is True
    await h.browser(bytes=_pcm())
    assert len(h.live.audio_in) == 1                  # the user's speech goes through
    await h.server(sc(output_transcription=NS(text="FY24 total", finished=False)))
    assert h.of_type("agent_transcript") == [], "speak transcripts are dropped until its turn_complete"
    await h.server(sc(turn_complete=True))
    done = h.of_type("turn_complete")
    assert done and done[-1]["speak_id"] == "S1" and done[-1]["metrics"]["speak_only"] is True
    assert h.mgr._is_speak_only is False and h.mgr._speak_id is None and h.mgr._barge_in_open is False
    await h.stop()


@pytest.mark.asyncio
async def test_server_interrupted_ends_the_speak_and_reports_its_id():
    h = Harness()
    await h.start()
    await h.browser(type="speak", text="Hello there.", speak_id="S2")
    await h.server(audio_turn())
    await h.server(sc(interrupted=True))
    ev = h.of_type("interrupted")
    assert ev and ev[-1]["speak_id"] == "S2"
    assert h.mgr._is_speak_only is False and h.mgr._speak_id is None
    assert h.mgr._mic_gate_open() is True
    await h.stop()


@pytest.mark.asyncio
async def test_normal_voice_turn_transcripts_still_flow():
    h = Harness()
    await h.start()
    await h.browser(bytes=_pcm())                     # user speaks (gate open)
    assert len(h.live.audio_in) == 1
    await h.server(sc(input_transcription=NS(text="Headcount in Delhi", finished=True)))
    await h.server(sc(output_transcription=NS(text="Delhi has 692 executives.", finished=True)))
    assert [m["text"] for m in h.of_type("agent_transcript")] == ["Delhi has 692 executives."]
    await h.stop()


# ---------------------------------------------------------------- P0.10 r2 (G4 MF-2, MF-3, S-3)
@pytest.mark.asyncio
async def test_new_stream_resets_stale_gate_state():
    """MF-2: a reconnect mid-reply/mid-speak must not leave the gate shut forever."""
    h = Harness()
    m = h.mgr
    m._generating, m._is_speak_only, m._speak_id, m._speak_queue = True, True, "OLD", ["OLD"]
    m._barge_in_open, m._playback_until = True, ls.time.perf_counter() + 60
    await h.start()
    assert (m._generating, m._is_speak_only, m._speak_id, m._speak_queue, m._barge_in_open) == (False, False, None, [], False)
    assert m._playback_until == 0.0 and m._mic_gate_open() is True
    await h.browser(bytes=_pcm())
    assert len(h.live.audio_in) == 1
    await h.stop()


def test_gate_watchdog_reopens_after_8s_without_server_events():
    """MF-2: no Live event for > 8 s while 'generating' or 'speaking' -> stale, gate re-opens."""
    m = Harness().mgr
    m._generating, m._is_speak_only, m._speak_queue = True, True, ["S9"]
    m._last_server_event = ls.time.perf_counter() - 1.0
    assert m._mic_gate_open() is False                      # recent event: still closed
    m._last_server_event = ls.time.perf_counter() - (ls.GATE_WATCHDOG_S + 0.5)
    assert m._mic_gate_open() is True                       # stale: re-opened
    assert (m._generating, m._is_speak_only, m._speak_queue) == (False, False, [])


@pytest.mark.asyncio
async def test_new_reply_closes_a_leftover_barge_in():
    """MF-3: an `interrupt` sent while idle (mic start, typed turn, late tap) must not keep the backend gate open
    through the NEXT reply's generation."""
    h = Harness()
    await h.start()
    await h.browser(type="interrupt")                       # e.g. mic start: browser always sends interrupt
    assert h.mgr._barge_in_open is True
    await h.server(audio_turn())                            # the next reply starts
    assert h.mgr._barge_in_open is False
    await h.browser(bytes=_pcm())
    assert h.live.audio_in == [], "echo during the new reply must be gated"
    await h.stop()


@pytest.mark.asyncio
async def test_barge_in_during_generation_survives_further_model_parts():
    h = Harness()
    await h.start()
    await h.server(audio_turn())                            # Yukti is generating
    await h.browser(type="interrupt")                       # user taps Stop mid-reply
    await h.server(audio_turn())                            # more parts of the SAME reply arrive
    assert h.mgr._barge_in_open is True
    await h.browser(bytes=_pcm())
    assert len(h.live.audio_in) == 1                        # the user's speech goes through
    await h.stop()


@pytest.mark.asyncio
async def test_two_queued_speaks_complete_in_order():
    """S-3: a second speak no longer overwrites the first one's id."""
    h = Harness()
    await h.start()
    await h.browser(type="speak", text="First answer.", speak_id="A")
    await h.browser(type="speak", text="Second answer.", speak_id="B")
    await h.server(audio_turn())
    await h.server(sc(turn_complete=True))
    assert h.of_type("turn_complete")[-1]["speak_id"] == "A"
    assert h.mgr._is_speak_only is True and h.mgr._speak_id == "B"
    await h.server(audio_turn())
    await h.server(sc(turn_complete=True))
    assert h.of_type("turn_complete")[-1]["speak_id"] == "B"
    assert h.mgr._is_speak_only is False and h.mgr._speak_id is None
    await h.stop()
