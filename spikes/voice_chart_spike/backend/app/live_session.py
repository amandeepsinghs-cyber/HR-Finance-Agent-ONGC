"""WebSocket bidirectional streaming session handler using Google ADK run_live / LiveRequestQueue.
Integrates LiveRequestQueue, speech config, input/output transcription, tools, and live ADK events.
"""

import asyncio
import base64
import json
import logging
import os
import struct
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Enforce project and location for Vertex AI ADK live connection
os.environ["GOOGLE_CLOUD_PROJECT"] = "ongc-hr-finance-agent"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

from fastapi import WebSocket, WebSocketDisconnect
from google.adk.agents.live_request_queue import LiveRequest, LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from app.agent import create_ongc_agent, DEFAULT_LIVE_MODEL, DEFAULT_VOICE
from app.tools.bq_headcount import query_headcount_tenure
from app.tools.policy_search import search_policy

logger = logging.getLogger("voice_chart_spike.live_session")


class LiveSessionManager:
    """Manages an active WebSocket bidi-streaming session for the voice-to-chart spike."""

    def __init__(
        self,
        websocket: WebSocket,
        model_name: str = DEFAULT_LIVE_MODEL,
        voice: str = DEFAULT_VOICE,
        language: str = "en-IN",
    ):
        self.ws = websocket
        self.model_name = model_name
        self.voice = voice
        self.language = language
        self.project_id = "ongc-hr-finance-agent"
        self.location = "us-central1"
        self.session_service = InMemorySessionService()
        self.agent = create_ongc_agent(model_name=self.model_name)
        self.runner = Runner(
            agent=self.agent,
            app_name=self.agent.name,
            session_service=self.session_service
        )
        self.live_queue = LiveRequestQueue()
        self.active = True
        self.t_turn_start = None
        self.t_tool_start = None

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

    async def run(self) -> None:
        session_id = f"spike-session-{int(time.time()*1000)}"
        user_id = "spike-engineer"
        
        session = await self.session_service.create_session(
            app_name=self.agent.name,
            user_id=user_id,
            session_id=session_id
        )

        run_config = self._build_run_config()

        await self.send_json({
            "type": "connection_status",
            "status": "ready",
            "session_id": session_id,
            "model": self.model_name,
            "voice": self.voice,
            "language": self.language,
            "project": self.project_id,
            "location": self.location,
            "mode": "live_cloud"
        })

        async def forward_adk_events():
            t_first_audio_ms = None
            t_tool_start_ms = None
            t_chart_ready_ms = None
            tool_duration_ms = None
            total_audio_bytes = 0

            try:
                logger.info(f"Connecting to live runner for model {self.model_name}...")
                async for event in self.runner.run_live(
                    session=session,
                    live_request_queue=self.live_queue,
                    run_config=run_config
                ):
                    t_event = time.perf_counter()

                    # 1. Tool Call Event from Live Model
                    f_calls = event.get_function_calls()
                    if f_calls:
                        for fc in f_calls:
                            self.t_tool_start = t_event
                            if self.t_turn_start:
                                t_tool_start_ms = round((t_event - self.t_turn_start) * 1000, 2)
                            await self.send_json({
                                "type": "tool_call_start",
                                "tool": fc.name,
                                "args": fc.args,
                                "timestamp_ms": t_tool_start_ms
                            })

                    # 2. Tool Response Event (After ADK executed tool)
                    f_resps = event.get_function_responses()
                    if f_resps:
                        for fr in f_resps:
                            if self.t_tool_start:
                                tool_duration_ms = round((t_event - self.t_tool_start) * 1000, 2)
                            resp_val = fr.response or {}
                            summary = resp_val.get("summary") if isinstance(resp_val, dict) else str(resp_val)
                            
                            await self.send_json({
                                "type": "tool_call_done",
                                "tool": fr.name,
                                "latency_ms": tool_duration_ms,
                                "summary": summary
                            })

                            # Check for chart spec in tool response
                            if isinstance(resp_val, dict) and "chart_spec" in resp_val:
                                if self.t_turn_start:
                                    t_chart_ready_ms = round((t_event - self.t_turn_start) * 1000, 2)
                                await self.send_json({
                                    "type": "chart_spec",
                                    "chart_type": "echarts",
                                    "spec": resp_val["chart_spec"],
                                    "timestamp_ms": t_chart_ready_ms
                                })

                    # 3. Model Content / Transcripts / Audio
                    if event.content and event.content.parts:
                        for p in event.content.parts:
                            if p.text:
                                await self.send_json({
                                    "type": "agent_transcript",
                                    "text": p.text,
                                    "is_final": False
                                })
                            if p.inline_data and p.inline_data.data:
                                chunk = p.inline_data.data
                                total_audio_bytes += len(chunk)
                                if t_first_audio_ms is None and self.t_turn_start:
                                    t_first_audio_ms = round((t_event - self.t_turn_start) * 1000, 2)
                                await self.send_audio_chunk(chunk)

                    # 4. Turn Complete
                    if event.turn_complete:
                        t_complete_ms = None
                        if self.t_turn_start:
                            t_complete_ms = round((t_event - self.t_turn_start) * 1000, 2)

                        await self.send_json({
                            "type": "turn_complete",
                            "metrics": {
                                "ttfb_audio_ms": t_first_audio_ms,
                                "tool_start_ms": t_tool_start_ms,
                                "tool_duration_ms": tool_duration_ms,
                                "chart_ready_ms": t_chart_ready_ms,
                                "turn_total_ms": t_complete_ms,
                                "audio_bytes_total": total_audio_bytes,
                                "model_used": self.model_name,
                                "mode": "true_live_adk"
                            }
                        })
                        # Reset turn timers
                        self.t_turn_start = None
                        t_first_audio_ms = None
                        t_tool_start_ms = None
                        t_chart_ready_ms = None
                        total_audio_bytes = 0

            except Exception as exc:
                logger.exception(f"Exception in forward_adk_events: {exc}")
                await self.send_json({
                    "type": "error",
                    "error": str(exc),
                    "model": self.model_name
                })

        event_task = asyncio.create_task(forward_adk_events())

        try:
            while self.active:
                raw_msg = await self.ws.receive_text()
                msg = json.loads(raw_msg)
                msg_type = msg.get("type")

                if msg_type == "config":
                    if "language" in msg:
                        self.language = msg["language"]
                    if "voice" in msg:
                        self.voice = msg["voice"]
                    await self.send_json({
                        "type": "config_updated",
                        "language": self.language,
                        "voice": self.voice
                    })

                elif msg_type == "text":
                    query_text = msg.get("text", "")
                    self.t_turn_start = time.perf_counter()
                    await self.send_json({
                        "type": "user_transcript",
                        "text": query_text,
                        "is_final": True
                    })
                    content = types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=query_text)]
                    )
                    self.live_queue.send(LiveRequest(content=content))

                elif msg_type == "audio":
                    # Inbound audio frame from AudioWorklet (16kHz PCM)
                    raw_b64 = msg.get("data", "")
                    audio_bytes = base64.b64decode(raw_b64)
                    blob = types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
                    self.live_queue.send(LiveRequest(blob=blob))

                elif msg_type == "audio_stream_end":
                    # Mark end of user speech as t0 for audio streaming turns
                    self.t_turn_start = time.perf_counter()
                    self.live_queue.send(LiveRequest(audio_stream_end=True))

                elif msg_type == "ping":
                    await self.send_json({"type": "pong", "time": time.time()})

        except WebSocketDisconnect:
            logger.info("Client disconnected from Live WebSocket.")
        except Exception as e:
            logger.exception(f"Exception in WebSocket loop: {e}")
        finally:
            self.active = False
            event_task.cancel()
