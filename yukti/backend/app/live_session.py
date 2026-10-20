"""Bidirectional Live Streaming WebSocket Session Manager for Yukti AI.
Implements Google ADK run_live with LiveRequestQueue, Leda 24 kHz speech synthesis,
real-time tool call status events, spoken holding phrases, and Answer Contract JSON emission.
"""

import asyncio
import base64
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional
from fastapi import WebSocket, WebSocketDisconnect
from google.adk.agents.live_request_queue import LiveRequest, LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from app.agent import create_yukti_agent
from app.answer_composer import detect_language
from app.config import (
    DEFAULT_LIVE_MODEL,
    DEFAULT_VOICE,
    GCP_PROJECT,
    VERTEX_LOCATION,
)
from app.session_memory import get_session_manager

logger = logging.getLogger("yukti.live_session")


class LiveSessionManager:
    """Manages an active WebSocket bidi-streaming session for Yukti AI."""

    def __init__(
        self,
        websocket: WebSocket,
        session_id: str,
        persona: str = "CMD",
        model_name: str = DEFAULT_LIVE_MODEL,
        voice: str = DEFAULT_VOICE,
        language: str = "en",
    ):
        self.ws = websocket
        self.session_id = session_id
        self.persona = persona
        self.model_name = model_name
        self.voice = voice
        self.language = language

        self.session_service = InMemorySessionService()
        self.agent = create_yukti_agent(model_name=self.model_name)
        self.runner = Runner(
            agent=self.agent,
            app_name=self.agent.name,
            session_service=self.session_service,
        )
        self.live_queue = LiveRequestQueue()
        self.active = True
        self.session_state = get_session_manager().get_or_create(
            session_id=session_id,
            persona=persona,
            language=language,
        )
        self.t_turn_start = None
        self.t_tool_start = None
        self.current_query_text = ""

    async def send_json(self, payload: Dict[str, Any]) -> None:
        try:
            await self.ws.send_text(json.dumps(payload, default=str))
        except Exception as e:
            logger.warning(f"Error sending json over websocket: {e}")

    async def send_audio_chunk(self, pcm_bytes: bytes) -> None:
        payload = {
            "type": "audio",
            "data": base64.b64encode(pcm_bytes).decode("ascii"),
            "sample_rate": 24000,
        }
        await self.send_json(payload)

    def _build_run_config(self) -> RunConfig:
        voice_cfg = types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.voice)
        )
        speech_cfg = types.SpeechConfig(voice_config=voice_cfg)
        return RunConfig(
            response_modalities=["AUDIO"],
            speech_config=speech_cfg,
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
        )

    async def send_opening_greeting(self) -> None:
        """Emits the UX Spec §14 opening greeting on session start."""
        if self.language == "hi":
            greeting_spoken = "नमस्ते, मैं युक्ति हूँ, आपकी एचआर और वित्त सलाहकार। कृपया बताइए मैं आपकी क्या सहायता कर सकती हूँ।"
            greeting_display = "नमस्ते, मैं युक्ति हूँ। मैं आपकी क्या सहायता कर सकती हूँ?"
        else:
            greeting_spoken = "Hello, I am Yukti, your HR and Finance agent. Please tell me how I can help."
            greeting_display = "Hello, I am Yukti, your HR & Finance agent. How can I assist you today?"

        greeting_contract = {
            "turn_id": f"turn-{self.session_id}-000",
            "language": self.language,
            "persona": self.persona,
            "spoken_summary": greeting_spoken,
            "display_text": greeting_display,
            "visual": {
                "type": "none",
                "mode": "replace",
            },
            "insights": ["Yukti AI connected", "Role: " + self.persona],
            "sources": [{"kind": "data", "object": "ONGC Enterprise Data Bank"}],
            "suggestions": [
                "How many executives in Delhi >= 5 years?",
                "Which fields are loss-making?",
                "What are the station tenure transfer norms?",
            ],
            "access": {"status": "allowed"},
            "export_options": ["sheets", "docs", "word", "pdf"],
            "status_events": ["Yukti AI ready"],
        }
        await self.send_json({
            "type": "contract",
            "contract": greeting_contract,
        })

    async def run(self) -> None:
        # Enforce region us-central1 where Vertex AI Live models reside
        os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
        user_id = f"user-{self.persona.lower()}"
        session = await self.session_service.create_session(
            app_name=self.agent.name,
            user_id=user_id,
            session_id=self.session_id,
        )

        run_config = self._build_run_config()

        await self.send_json({
            "type": "connection_status",
            "status": "ready",
            "session_id": self.session_id,
            "model": self.model_name,
            "voice": self.voice,
            "persona": self.persona,
            "language": self.language,
        })

        await self.send_opening_greeting()

        async def forward_adk_events():
            t_first_audio_ms = None
            t_tool_start_ms = None
            tool_duration_ms = None
            total_audio_bytes = 0
            tool_calls_recorded = []
            tool_responses_recorded = []
            agent_transcripts = []

            try:
                logger.info(f"Initiating live runner connection (Model: {self.model_name}, Voice: {self.voice})...")
                async for event in self.runner.run_live(
                    session=session,
                    live_request_queue=self.live_queue,
                    run_config=run_config,
                ):
                    t_event = time.perf_counter()

                    # 1. Tool Call Event from Model
                    f_calls = event.get_function_calls()
                    if f_calls:
                        for fc in f_calls:
                            self.t_tool_start = t_event
                            if self.t_turn_start:
                                t_tool_start_ms = round((t_event - self.t_turn_start) * 1000, 2)
                            tool_calls_recorded.append({"name": fc.name, "args": fc.args})
                            
                            # Push status event to UI
                            await self.send_json({
                                "type": "status_event",
                                "status": f"Executing {fc.name}: {str(fc.args)[:50]}...",
                            })
                            await self.send_json({
                                "type": "tool_call_start",
                                "tool": fc.name,
                                "args": fc.args,
                                "timestamp_ms": t_tool_start_ms,
                            })

                    # 2. Tool Response Event
                    f_resps = event.get_function_responses()
                    if f_resps:
                        for fr in f_resps:
                            if self.t_tool_start:
                                tool_duration_ms = round((t_event - self.t_tool_start) * 1000, 2)
                            tool_responses_recorded.append({"name": fr.name, "response": fr.response})
                            await self.send_json({
                                "type": "status_event",
                                "status": f"Tool {fr.name} finished ({tool_duration_ms} ms).",
                            })
                            await self.send_json({
                                "type": "tool_call_done",
                                "tool": fr.name,
                                "latency_ms": tool_duration_ms,
                                "response": fr.response,
                            })

                    # 3. Streamed Audio & Agent Transcripts
                    if event.content and event.content.parts:
                        for p in event.content.parts:
                            if p.text:
                                agent_transcripts.append(p.text)
                                await self.send_json({
                                    "type": "agent_transcript",
                                    "text": p.text,
                                    "is_final": False,
                                })
                            if p.inline_data and p.inline_data.data:
                                chunk = p.inline_data.data
                                total_audio_bytes += len(chunk)
                                if t_first_audio_ms is None and self.t_turn_start:
                                    t_first_audio_ms = round((t_event - self.t_turn_start) * 1000, 2)
                                await self.send_audio_chunk(chunk)

                    # 4. Turn Complete Event: Emit Composed Answer Contract JSON
                    if event.turn_complete:
                        t_complete_ms = None
                        if self.t_turn_start:
                            t_complete_ms = round((t_event - self.t_turn_start) * 1000, 2)

                        # Build Answer Contract JSON for canvas update
                        from app.turn_runner import get_agent_turn_runner
                        trun = get_agent_turn_runner()
                        full_tx = "".join(agent_transcripts).strip()
                        spoken_summary = trun._extract_spoken_summary(full_tx, self.language)

                        # Deterministic number verification
                        for tr in tool_responses_recorded:
                            if tr["name"] == "query_data":
                                det_sum = tr["response"].get("deterministic_summary", {})
                                total_cnt = det_sum.get("total_count")
                                if total_cnt is not None:
                                    model_nums = re.findall(r"\b\d+\b", spoken_summary)
                                    if model_nums and str(total_cnt) not in model_nums and not any(abs(float(n) - total_cnt) <= 1 for n in model_nums):
                                        top_text = det_sum.get("top_ranked_text", "")
                                        spoken_summary = (
                                            f"According to enterprise records in hrfin_gold, a total of {total_cnt} matching records were found. "
                                            f"{top_text}. Please refer to the interactive visual on your canvas for the complete breakdown."
                                        )
                                break

                        visual_mode = self.session_state.resolve_visual_mode(entry_id=None, query=self.current_query_text)
                        visual, sources = trun._build_visual_and_sources(
                            tool_calls=tool_calls_recorded,
                            tool_responses=tool_responses_recorded,
                            query=self.current_query_text,
                            visual_mode=visual_mode,
                            voice_override=None,
                        )

                        turn_index = len(self.session_state.turns) + 1
                        turn_id = f"turn-{self.session_id}-{turn_index:03d}"
                        primary_source = sources[0].get("object") or sources[0].get("doc_id") or "Enterprise Records"

                        contract = {
                            "turn_id": turn_id,
                            "language": self.language,
                            "persona": self.persona,
                            "spoken_summary": spoken_summary,
                            "display_text": f"{spoken_summary[:500]} [1].",
                            "visual": visual,
                            "insights": [f"Grounding: {primary_source}", f"Voice turn completed on {self.model_name}"],
                            "sources": sources,
                            "suggestions": ["Show by discipline", "What are the relevant policy rules?"],
                            "access": {"status": "allowed"},
                            "export_options": ["sheets", "xlsx", "pdf"] if visual.get("type") != "document" else ["docs", "word", "pdf"],
                            "status_events": ["Voice turn complete", "Canvas visual updated"],
                        }

                        trun.validator.validate(contract)
                        self.session_state.record_turn(contract)

                        # Emit contract for frontend canvas update
                        await self.send_json({
                            "type": "contract",
                            "contract": contract,
                        })

                        await self.send_json({
                            "type": "turn_complete",
                            "metrics": {
                                "ttfb_audio_ms": t_first_audio_ms,
                                "tool_start_ms": t_tool_start_ms,
                                "tool_duration_ms": tool_duration_ms,
                                "turn_total_ms": t_complete_ms,
                                "audio_bytes_total": total_audio_bytes,
                                "model_used": self.model_name,
                            },
                        })

                        # Reset turn state
                        self.t_turn_start = None
                        t_first_audio_ms = None
                        t_tool_start_ms = None
                        total_audio_bytes = 0
                        tool_calls_recorded = []
                        tool_responses_recorded = []
                        agent_transcripts = []

            except Exception as exc:
                logger.exception(f"Error in forward_adk_events: {exc}")
                await self.send_json({
                    "type": "error",
                    "message": str(exc),
                    "retryable": True,
                })

        event_task = asyncio.create_task(forward_adk_events())

        try:
            while self.active:
                raw_msg = await self.ws.receive_text()
                msg = json.loads(raw_msg)
                msg_type = msg.get("type")

                if msg_type == "config":
                    if "persona" in msg:
                        self.persona = msg["persona"]
                        self.session_state.persona = msg["persona"]
                    if "language" in msg:
                        self.language = msg["language"]
                        self.session_state.language = msg["language"]
                    if "voice" in msg:
                        self.voice = msg["voice"]
                    await self.send_json({
                        "type": "config_updated",
                        "persona": self.persona,
                        "language": self.language,
                        "voice": self.voice,
                    })

                elif msg_type == "text":
                    query_text = msg.get("text", "")
                    self.current_query_text = query_text
                    self.t_turn_start = time.perf_counter()
                    await self.send_json({
                        "type": "user_transcript",
                        "text": query_text,
                        "is_final": True,
                    })

                    # Send to Live runner for speech audio generation
                    content = types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=query_text)],
                    )
                    self.live_queue.send(LiveRequest(content=content))

                elif msg_type == "audio":
                    raw_b64 = msg.get("data", "")
                    audio_bytes = base64.b64decode(raw_b64)
                    blob = types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
                    self.live_queue.send(LiveRequest(blob=blob))

                elif msg_type == "audio_stream_end":
                    self.t_turn_start = time.perf_counter()
                    self.live_queue.send(LiveRequest(audio_stream_end=True))

                elif msg_type == "ping":
                    await self.send_json({"type": "pong", "time": time.time()})

        except WebSocketDisconnect:
            logger.info(f"WebSocket client disconnected: {self.session_id}")
        except Exception as e:
            logger.exception(f"Exception in WebSocket loop: {e}")
            await self.send_json({
                "type": "error",
                "message": str(e),
                "retryable": False,
            })
        finally:
            self.active = False
            event_task.cancel()
