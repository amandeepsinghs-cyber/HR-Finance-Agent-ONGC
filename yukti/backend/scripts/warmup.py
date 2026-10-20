#!/usr/bin/env python3
"""scripts/warmup.py — Warms the in-memory Option A Tool-Result cache for Yukti AI.
Sends the 89 root questions + follow-ups through /api/turn to populate the cache.
Prints hit/miss status, execution times, and final cache statistics.
"""

import asyncio
from pathlib import Path
import sys
import time
import requests
import yaml

BACKEND_DIR = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = BACKEND_DIR.parent.parent / "data_bank" / "world_bible" / "reference" / "questions.yaml"

BASE_URL = "http://127.0.0.1:8080"
REFUSAL_IDS = {"D1", "D2", "D3", "D4", "D5", "D6", "P18", "P19", "P20", "M3", "M4"}


def run_warmup():
    print("=" * 70)
    print("STARTING YUKTI AI TOOL-RESULT CACHE WARMUP")
    print(f"Server Target: {BASE_URL} | Questions: {QUESTIONS_PATH}")
    print("=" * 70)

    # 1. Verify health
    try:
        r_health = requests.get(f"{BASE_URL}/health", timeout=5).json()
        print(f"✓ Health Check OK: {r_health}")
    except Exception as e:
        print(f"ERROR: Cannot connect to {BASE_URL}. Ensure uvicorn server is running: {e}")
        return

    # 2. Load questions
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        questions = yaml.safe_load(f)["questions"]

    t_start = time.perf_counter()
    warmed = 0
    hits = 0
    misses = 0

    print(f"\nProcessing {len(questions)} root questions + follow-ups...\n")

    for idx, q in enumerate(questions, 1):
        qid = q["id"]
        qtext = q["question"]
        persona = "E2_HR" if qid in REFUSAL_IDS and qid != "P20" else ("DIR_HR" if qid == "P20" else "CMD")

        # 1. Warm root question
        t0 = time.perf_counter()
        try:
            res = requests.post(f"{BASE_URL}/api/turn", json={"query": qtext, "persona": persona}, timeout=30).json()
            elapsed = round((time.perf_counter() - t0) * 1000, 1)
            from_cache = any("recently fetched" in s.lower() for s in res.get("status_events", []))
            if from_cache:
                hits += 1
            else:
                misses += 1
            warmed += 1
            print(f"[{qid}] ({elapsed} ms) {'[CACHE HIT]' if from_cache else '[FETCHED]'} Tool: {res.get('tool_called')} | {qtext[:60]}...")
        except Exception as e:
            print(f"[{qid}] FAILED: {e}")

        # 2. Warm follow-ups in same conversation
        sess_id = f"warm-sess-{qid}"
        for fu in q.get("followups", []):
            futext = fu["question"]
            t0 = time.perf_counter()
            try:
                res_fu = requests.post(f"{BASE_URL}/api/turn", json={"query": futext, "session_id": sess_id, "persona": persona}, timeout=30).json()
                elapsed = round((time.perf_counter() - t0) * 1000, 1)
                from_cache = any("recently fetched" in s.lower() for s in res_fu.get("status_events", []))
                if from_cache:
                    hits += 1
                else:
                    misses += 1
                warmed += 1
            except Exception:
                pass

    total_time = round(time.perf_counter() - t_start, 1)

    # 3. Print Cache Statistics
    try:
        stats = requests.get(f"{BASE_URL}/admin/cache", timeout=5).json()
        print("\n" + "=" * 70)
        print("WARMUP COMPLETED")
        print("=" * 70)
        print(f"Total Requests Sent: {warmed} in {total_time}s")
        print(f"Cache Stats: {stats}")
        print("=" * 70)
    except Exception as e:
        print("Error fetching cache stats:", e)


if __name__ == "__main__":
    run_warmup()
