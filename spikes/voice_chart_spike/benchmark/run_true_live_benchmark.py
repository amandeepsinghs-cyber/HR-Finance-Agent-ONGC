"""True Live Benchmark Runner for ONGC Voice-to-Chart Spike.
Exercises live Gemini Live native-audio models on Vertex AI us-central1 (gemini-3.8-live and gemini-live-2.5-flash-native-audio),
streaming real 16kHz PCM audio clips and measuring:
- time from end-of-user-speech to model tool_call event
- tool execution time (real BigQuery / Vertex AI Search)
- time to declarative ECharts chart_spec delivery
- time to first audio byte (TTFB audio)
- turn_complete
"""

import asyncio
import base64
import json
import logging
import os
import time
import wave
from pathlib import Path
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("true_live_benchmark")

TEST_AUDIO_DIR = Path(__file__).resolve().parent.parent / "test_audio"
OUTPUT_LIVE_FILE = Path(__file__).resolve().parent / "benchmark_results_true_live.json"


async def stream_audio_clip(ws, wav_path: Path):
    """Streams 16kHz mono PCM frames in 100ms chunks (3200 bytes) over WebSocket."""
    with wave.open(str(wav_path), "rb") as wf:
        raw = wf.readframes(wf.getnframes())
    
    chunk_size = 3200
    for i in range(0, len(raw), chunk_size):
        chunk = raw[i:i+chunk_size]
        b64_data = base64.b64encode(chunk).decode("ascii")
        await ws.send(json.dumps({"type": "audio", "data": b64_data}))
        await asyncio.sleep(0.04)  # stream slightly faster than real-time for benchmark stability

    # Mark end of speech
    t_end_of_speech = time.perf_counter()
    await ws.send(json.dumps({"type": "audio_stream_end"}))
    return t_end_of_speech


async def run_live_test_case(model_name: str, test_id: str, mode: str, input_val: str, lang: str = "en-IN") -> dict:
    url = f"ws://localhost:8100/ws/live?model={model_name}&voice=Aoede&language={lang}"
    logger.info(f"[{test_id}] Connecting to {url}...")
    
    async with websockets.connect(url) as ws:
        init_raw = await ws.recv()
        logger.info(f"  Connected: {init_raw}")

        t0 = None
        if mode == "audio":
            wav_path = TEST_AUDIO_DIR / input_val
            logger.info(f"  Streaming audio clip: {wav_path.name}...")
            t0 = await stream_audio_clip(ws, wav_path)
        else:
            logger.info(f"  Sending text message: '{input_val[:50]}'...")
            t0 = time.perf_counter()
            await ws.send(json.dumps({"type": "text", "text": input_val}))

        t_tool_call = None
        t_chart_spec = None
        t_first_audio = None
        t_complete = None
        tool_name = None
        tool_duration_ms = None
        total_audio_bytes = 0
        agent_transcript = ""

        while True:
            try:
                raw_event = await asyncio.wait_for(ws.recv(), timeout=25.0)
                evt = json.loads(raw_event)
                t_recv = time.perf_counter()
                evt_type = evt.get("type")

                if evt_type == "tool_call_start":
                    if t_tool_call is None:
                        t_tool_call = round((t_recv - t0) * 1000, 2)
                        tool_name = evt.get("tool")
                        logger.info(f"  [+{t_tool_call}ms] Tool call started: {tool_name}")

                elif evt_type == "tool_call_done":
                    tool_duration_ms = evt.get("latency_ms")
                    logger.info(f"  Tool execution done in {tool_duration_ms}ms")

                elif evt_type == "chart_spec":
                    if t_chart_spec is None:
                        t_chart_spec = round((t_recv - t0) * 1000, 2)
                        logger.info(f"  [+{t_chart_spec}ms] ECharts spec received")

                elif evt_type == "audio":
                    chunk_len = len(base64.b64decode(evt.get("data", "")))
                    total_audio_bytes += chunk_len
                    if t_first_audio is None:
                        t_first_audio = round((t_recv - t0) * 1000, 2)
                        logger.info(f"  [+{t_first_audio}ms] First model audio byte received")

                elif evt_type == "agent_transcript":
                    agent_transcript += evt.get("text", "")

                elif evt_type == "turn_complete":
                    t_complete = round((t_recv - t0) * 1000, 2)
                    metrics = evt.get("metrics", {})
                    logger.info(f"  [+{t_complete}ms] Turn complete. Metrics: {metrics}")
                    break

            except asyncio.TimeoutError:
                logger.warning(f"  Timeout waiting for turn completion on {test_id}")
                break

        return {
            "test_id": test_id,
            "model": model_name,
            "mode": mode,
            "language": lang,
            "input": input_val,
            "tool_called": tool_name,
            "time_to_tool_call_ms": t_tool_call,
            "tool_duration_ms": tool_duration_ms,
            "time_to_chart_rendered_ms": t_chart_spec,
            "time_to_first_audio_ms": t_first_audio,
            "total_turn_ms": t_complete,
            "audio_bytes_total": total_audio_bytes,
            "agent_transcript": agent_transcript[:120]
        }


async def main():
    results = []

    # 1. Compare models: gemini-3.8-live vs gemini-live-2.5-flash-native-audio on primary question
    logger.info("=== STEP 1: Model Comparison (gemini-3.8-live vs gemini-live-2.5-flash-native-audio) ===")
    res_38 = await run_live_test_case(
        model_name="gemini-3.8-live",
        test_id="COMPARE-GEMINI-3.8",
        mode="text",
        input_val="How many executives have been posted in Delhi for 5 years or more? Break down by grade and discipline."
    )
    results.append(res_38)
    await asyncio.sleep(1)

    res_flash = await run_live_test_case(
        model_name="gemini-live-2.5-flash-native-audio",
        test_id="COMPARE-FLASH-NATIVE",
        mode="text",
        input_val="How many executives have been posted in Delhi for 5 years or more? Break down by grade and discipline."
    )
    results.append(res_flash)
    await asyncio.sleep(1)

    # 2. Real audio streaming tests with recorded clips (16kHz PCM)
    logger.info("\n=== STEP 2: Live Audio Streaming Benchmark (PCM via AudioWorklet path) ===")
    res_audio_en = await run_live_test_case(
        model_name="gemini-3.8-live",
        test_id="AUDIO-EN-1",
        mode="audio",
        input_val="delhi_5yr_en.wav",
        lang="en-IN"
    )
    results.append(res_audio_en)
    await asyncio.sleep(1)

    res_audio_hi = await run_live_test_case(
        model_name="gemini-3.8-live",
        test_id="AUDIO-HI-1",
        mode="audio",
        input_val="delhi_5yr_hi.wav",
        lang="hi-IN"
    )
    results.append(res_audio_hi)
    await asyncio.sleep(1)

    # 3. Follow-up and Policy questions
    logger.info("\n=== STEP 3: Follow-up & Policy Questions ===")
    res_fu = await run_live_test_case(
        model_name="gemini-3.8-live",
        test_id="TEXT-FOLLOWUP",
        mode="text",
        input_val="only E5 and above"
    )
    results.append(res_fu)
    await asyncio.sleep(1)

    res_pol = await run_live_test_case(
        model_name="gemini-3.8-live",
        test_id="TEXT-POLICY",
        mode="text",
        input_val="how long must I stay at a station before transfer?"
    )
    results.append(res_pol)

    OUTPUT_LIVE_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")
    logger.info(f"\nSaved true live benchmark results to {OUTPUT_LIVE_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
