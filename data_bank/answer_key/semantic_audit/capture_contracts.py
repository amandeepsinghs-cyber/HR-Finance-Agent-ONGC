"""Capture FULL agent contracts for the 773 Track-C turns (read-only use of yukti code).

The official eval (yukti/backend/eval/run_eval.py) persists only 120 chars of spoken text, no table rows and no
sources, which is not enough evidence to score numbers, periods or policy clauses. This harness replays exactly the
same turns (same personas, same session structure, caches OFF) through yukti's AgentTurnRunner and stores the whole
contract per turn, so semantic_audit/score_agent.py can score it.

Run (from yukti/backend, using yukti's environment; nothing in yukti is modified):
    uv run python "<data_bank>/answer_key/semantic_audit/capture_contracts.py" --out <file.jsonl> [--concurrency 5]
Resumable: entries already present in --out are skipped.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

os.environ["YUKTI_RESULT_CACHE"] = "0"
os.environ["YUKTI_DEMO_CACHE"] = "0"

BACKEND = Path.cwd()
sys.path.insert(0, str(BACKEND))

import yaml  # noqa: E402

from app.turn_runner import get_agent_turn_runner  # noqa: E402

DATA_BANK = Path(__file__).resolve().parents[2]
QUESTIONS = DATA_BANK / "world_bible" / "reference" / "questions.yaml"
PARAS = DATA_BANK / "answer_key" / "paraphrases.yaml"
STRESS = DATA_BANK / "reports" / "stress_test.md"
REFUSAL_IDS = {"D1", "D2", "D3", "D4", "D5", "D6", "P18", "P19", "P20", "M3", "M4"}  # mirrors run_eval.py


def stress_prompts():
    out = []
    for line in STRESS.read_text(encoding="utf-8").splitlines():
        if line.startswith("| ") and not line.startswith("| #") and not line.startswith("|---"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 8 and parts[0].isdigit():
                out.append({"idx": int(parts[0]), "persona": parts[1], "prompt": parts[2]})
    return out


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--concurrency", type=int, default=5)
    ap.add_argument("--model", default=os.getenv("YUKTI_EVAL_MODEL", "gemini-2.5-flash"))
    a = ap.parse_args()
    out = Path(a.out)
    done = set()
    if out.exists():
        for l in out.read_text(encoding="utf-8").splitlines():
            try:
                done.add(json.loads(l)["entry_id"])
            except Exception:  # noqa: BLE001
                pass
    runner = get_agent_turn_runner(model_name=a.model)
    sem = asyncio.Semaphore(a.concurrency)
    lock = asyncio.Lock()
    qs = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))["questions"]
    paras = yaml.safe_load(PARAS.read_text(encoding="utf-8"))["paraphrases"]

    async def save(eid, suite, persona, query, contract, err=None):
        rec = {"entry_id": eid, "suite": suite, "persona_tested": persona, "query": query,
               "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "error": err}
        if contract:
            rec.update({k: contract.get(k) for k in contract})
        async with lock:
            with open(out, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, default=str) + "\n")

    async def turn(eid, suite, query, sess, persona):
        if eid in done:
            return
        async with sem:
            try:
                c = await runner.execute_turn_async(query=query, session_id=sess, persona=persona)
                await save(eid, suite, persona, query, c)
            except Exception as e:  # noqa: BLE001
                await save(eid, suite, persona, query, None, str(e)[:500])

    tasks = []
    for q in qs:
        qid = q["id"]
        persona = "E2_HR" if qid in REFUSAL_IDS and qid != "P20" else ("DIR_HR" if qid == "P20" else "CMD")
        tasks.append(turn(qid, "root", q["question"], f"cap-root-{qid}", persona))

    async def conv(q):
        fids = [f"{q['id']}__{fu['kind']}" for fu in q.get("followups", [])]
        if all(f in done for f in fids):
            return
        sess = f"cap-fu-{q['id']}"
        async with sem:
            try:
                await runner.execute_turn_async(q["question"], session_id=sess, persona="CMD")
            except Exception:  # noqa: BLE001
                pass
        for fu in q.get("followups", []):
            await turn(f"{q['id']}__{fu['kind']}", "followups", fu["question"], sess, "CMD")

    tasks += [conv(q) for q in qs]
    for p in paras:
        for style in ("formal", "casual", "hinglish"):
            if p.get(style):
                pid = f"{p['id']}__{style}"
                tasks.append(turn(pid, "paraphrases", p[style], f"cap-para-{pid}", "CMD"))
    for st in stress_prompts():
        tasks.append(turn(f"ST-{st['idx']}", "stress_test", st["prompt"], f"cap-st-{st['idx']}", st["persona"]))
    await asyncio.gather(*tasks)
    print("capture complete:", out)


if __name__ == "__main__":
    asyncio.run(main())
