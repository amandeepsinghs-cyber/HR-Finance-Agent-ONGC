"""Test script to verify ADK runner.run_live with live Gemini Live native audio model,

tool calling, and audio response streaming.
"""

import asyncio
import os
import time
import wave
from pathlib import Path

os.environ["GOOGLE_CLOUD_PROJECT"] = "ongc-hr-finance-agent"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

from google.adk.agents.live_request_queue import LiveRequest, LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from app.agent import create_ongc_agent

PROJECT_ID = "ongc-hr-finance-agent"
LOCATION = "us-central1"
MODEL_ID = os.getenv("LIVE_MODEL", "gemini-3.8-live")
TEST_AUDIO_PATH = Path(__file__).resolve().parent.parent / "test_audio" / "delhi_5yr_en.wav"


async def main():
    print(f"Creating ADK ONGC Agent with model: {MODEL_ID} (Project: {PROJECT_ID}, Location: {LOCATION})...")
    agent = create_ongc_agent(model_name=MODEL_ID)
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name=agent.name, session_service=session_service)

    session = await session_service.create_session(
        app_name=agent.name,
        user_id="test-user",
        session_id=f"test-sess-{int(time.time())}"
    )

    live_queue = LiveRequestQueue()

    voice_cfg = types.VoiceConfig(
        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
    )
    speech_cfg = types.SpeechConfig(voice_config=voice_cfg)
    run_config = RunConfig(
        response_modalities=["AUDIO"],
        speech_config=speech_cfg,
        output_audio_transcription=types.AudioTranscriptionConfig(),
        input_audio_transcription=types.AudioTranscriptionConfig(),
    )

    print("Starting runner.run_live()...")
    t0 = time.perf_counter()

    async def event_consumer():
        audio_bytes_received = 0
        t_first_audio = None
        t_tool_call = None
        t_tool_resp = None
        tool_name = None

        try:
            async for event in runner.run_live(
                session=session,
                live_request_queue=live_queue,
                run_config=run_config
            ):
                t_event = time.perf_counter()
                f_calls = event.get_function_calls()
                if f_calls:
                    for fc in f_calls:
                        tool_name = fc.name
                        t_tool_call = round((t_event - t0) * 1000, 2)
                        print(f"  [+{t_tool_call}ms] Model issued function call: {fc.name}({fc.args})")

                f_resps = event.get_function_responses()
                if f_resps:
                    for fr in f_resps:
                        t_tool_resp = round((t_event - t0) * 1000, 2)
                        print(f"  [+{t_tool_resp}ms] Tool response executed: {fr.name}")

                if event.content and event.content.parts:
                    for p in event.content.parts:
                        if p.text:
                            print(f"  [Text chunk]: {p.text}")
                        if p.inline_data and p.inline_data.data:
                            chunk_len = len(p.inline_data.data)
                            audio_bytes_received += chunk_len
                            if t_first_audio is None:
                                t_first_audio = round((t_event - t0) * 1000, 2)
                                print(f"  [+{t_first_audio}ms] First model audio byte received ({chunk_len} bytes)")

                if event.turn_complete:
                    t_complete = round((t_event - t0) * 1000, 2)
                    print(f"  [+{t_complete}ms] Turn complete! Total audio received: {audio_bytes_received} bytes")
                    break
        except Exception as e:
            print("Error in consumer:", type(e).__name__, e)

    consumer_task = asyncio.create_task(event_consumer())

    # Send text prompt test first
    print("\n--- Sending text query to LiveRequestQueue ---")
    query_text = "How many executives have been posted in Delhi for 5 years or more? Break down by grade and discipline."
    content = types.Content(role="user", parts=[types.Part.from_text(text=query_text)])
    live_queue.send(LiveRequest(content=content))

    await asyncio.wait_for(consumer_task, timeout=30.0)


if __name__ == "__main__":
    asyncio.run(main())
