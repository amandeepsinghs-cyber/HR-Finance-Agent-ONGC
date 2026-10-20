"""Automated latency benchmark runner for ONGC Voice-to-Chart Spike.
Executes the test suite over WebSocket /ws/live and records:
- time from end-of-user-speech to tool-call start
- time to chart rendered (chart_spec delivered)
- time to first audio byte (TTFB audio)
- total turn duration
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List

import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("spike_benchmark")

WS_URL = "ws://localhost:8100/ws/live"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "benchmark_results_live.json")
MOCK_BACKUP_FILE = os.path.join(os.path.dirname(__file__), "benchmark_results_mock.json")

TEST_CASES = [
    {
        "id": "EN-1",
        "category": "headcount_english",
        "language": "en-IN",
        "text": "How many executives have been posted in Delhi for 5 years or more? Break down by grade and discipline.",
    },
    {
        "id": "EN-2",
        "category": "headcount_english",
        "language": "en-IN",
        "text": "How many executives have been posted in Delhi for 5 years or more? Break down by grade and discipline.",
    },
    {
        "id": "EN-3",
        "category": "headcount_english",
        "language": "en-IN",
        "text": "How many executives have been posted in Delhi for 5 years or more? Break down by grade and discipline.",
    },
    {
        "id": "EN-4",
        "category": "headcount_english",
        "language": "en-IN",
        "text": "How many executives have been posted in Delhi for 5 years or more? Break down by grade and discipline.",
    },
    {
        "id": "EN-5",
        "category": "headcount_english",
        "language": "en-IN",
        "text": "How many executives have been posted in Delhi for 5 years or more? Break down by grade and discipline.",
    },
    {
        "id": "HI-1",
        "category": "headcount_hinglish",
        "language": "hi-IN",
        "text": "Delhi mein 5 saal se zyada kitne executives hain, grade-wise batao",
    },
    {
        "id": "HI-2",
        "category": "headcount_hinglish",
        "language": "hi-IN",
        "text": "Delhi mein 5 saal se zyada kitne executives hain, grade-wise batao",
    },
    {
        "id": "FU-1",
        "category": "followup",
        "language": "en-IN",
        "text": "only E5 and above",
    },
    {
        "id": "POL-1",
        "category": "policy",
        "language": "en-IN",
        "text": "how long must I stay at a station before transfer?",
    },
]


async def run_single_test(ws: websockets.WebSocketClientProtocol, test_case: Dict[str, Any]) -> Dict[str, Any]:
    # Set language config
    await ws.send(json.dumps({
        "type": "config",
        "language": test_case["language"],
        "voice": "Aoede"
    }))
    
    # Wait briefly for config confirmation
    await asyncio.sleep(0.05)

    t0 = time.perf_counter()
    # Send user query simulation (end-of-speech milestone)
    await ws.send(json.dumps({
        "type": "query_simulate",
        "text": test_case["text"],
        "timestamp": t0
    }))

    t_tool_start = None
    t_first_audio = None
    t_chart_rendered = None
    t_turn_complete = None
    tool_name = None
    tool_latency_ms = None
    server_metrics = {}
    chart_view = None
    agent_text = ""

    while True:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
            msg = json.loads(raw)
            msg_type = msg.get("type")
            t_recv = time.perf_counter()

            if msg_type == "tool_call_start":
                if t_tool_start is None:
                    t_tool_start = round((t_recv - t0) * 1000, 2)
                    tool_name = msg.get("tool")

            elif msg_type == "tool_call_done":
                tool_latency_ms = msg.get("latency_ms")

            elif msg_type == "chart_spec":
                if t_chart_rendered is None:
                    t_chart_rendered = round((t_recv - t0) * 1000, 2)
                    chart_view = "donut+stacked_bar"

            elif msg_type == "audio":
                if t_first_audio is None:
                    t_first_audio = round((t_recv - t0) * 1000, 2)

            elif msg_type == "agent_transcript":
                agent_text = msg.get("text", "")

            elif msg_type == "turn_complete":
                t_turn_complete = round((t_recv - t0) * 1000, 2)
                server_metrics = msg.get("metrics", {})
                break

        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for response on test {test_case['id']}")
            break

    return {
        "id": test_case["id"],
        "category": test_case["category"],
        "language": test_case["language"],
        "query": test_case["text"],
        "tool_called": tool_name,
        "tool_latency_ms": tool_latency_ms,
        "time_to_tool_start_ms": t_tool_start,
        "time_to_chart_rendered_ms": t_chart_rendered,
        "time_to_first_audio_ms": t_first_audio,
        "total_turn_ms": t_turn_complete,
        "agent_transcript_preview": agent_text[:120],
        "server_metrics": server_metrics
    }


async def main():
    logger.info(f"Connecting to {WS_URL}...")
    async with websockets.connect(WS_URL) as ws:
        # Read initial ready message
        init_raw = await ws.recv()
        logger.info(f"Connected: {init_raw}")

        results = []
        for tc in TEST_CASES:
            logger.info(f"Running {tc['id']}: '{tc['text'][:50]}...' ({tc['language']})")
            res = await run_single_test(ws, tc)
            results.append(res)
            logger.info(
                f"  -> Tool: {res['tool_called']} | Start: {res['time_to_tool_start_ms']}ms | "
                f"Chart: {res['time_to_chart_rendered_ms']}ms | TTFB Audio: {res['time_to_first_audio_ms']}ms | Total: {res['total_turn_ms']}ms"
            )
            await asyncio.sleep(0.1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Benchmark results written to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
