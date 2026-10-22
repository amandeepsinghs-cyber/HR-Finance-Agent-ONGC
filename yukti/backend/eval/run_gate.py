"""Yukti AI fast gate eval (U0.4): ~120-turn cache-OFF subset of the full sweep.

Re-uses the scoring of `eval/run_eval.py` (FullEvaluator.score_entry, lenient
"overall_pass") and adds a stricter **anchor check**: for answered data entries,
at least one headline number from the frozen answer key (INDEX.md) must appear in
the answer (spoken/display text, KPI values, table or chart cells) within 1.5 %.

Usage (from yukti/backend):
    .venv/bin/python eval/run_gate.py --label U0 [--concurrency 6] [--out-dir DIR]

Writes `<out-dir>/<label>.json` (per-turn records + summary) and prints a
markdown scorecard; `eval/gates/<label>.md` is written from it by the operator.
The subset is frozen in `eval/gates/gate_subset.yaml`.
Flags such as YUKTI_PLANNER are read from the environment as usual.
"""

import argparse
import asyncio
import datetime
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["YUKTI_RESULT_CACHE"] = "0"
os.environ["YUKTI_DEMO_CACHE"] = "0"

import yaml  # noqa: E402

from eval.run_eval import CheckpointManager, FullEvaluator  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent
SUBSET_PATH = EVAL_DIR / "gates" / "gate_subset.yaml"
# A hung turn (network read error inside the ADK loop) counts as a failure instead of blocking the gate.
TURN_TIMEOUT_S = float(os.getenv("YUKTI_GATE_TURN_TIMEOUT", "150"))

_NUM_RE = re.compile(r"(?<![A-Za-z])-?\d[\d,]*(?:\.\d+)?")


def _to_float(tok: str) -> Optional[float]:
    try:
        return float(tok.replace(",", ""))
    except ValueError:
        return None


def headline_anchors(headline: str, max_n: int = 4) -> List[float]:
    """Significant numbers from an answer-key headline (skips years, FY labels, dates, tiny ints)."""
    text = re.sub(r"\bFY\s?\d{2,4}\b", " ", headline)
    text = re.sub(r"\b\d{1,2}-[A-Za-z]{3}-\d{4}\b", " ", text)
    text = re.sub(r"\bE\d\b|\bWC-[A-Z&]+\b|\bFLD-[A-Z]+\b|\bClause\s+[\d.]+", " ", text)
    out: List[float] = []
    for tok in _NUM_RE.findall(text):
        v = _to_float(tok)
        if v is None:
            continue
        if 1990 <= abs(v) <= 2040 and "." not in tok and "," not in tok:
            continue  # a year
        if abs(v) < 10 and "." not in tok:
            continue  # small integers ("5 years", "3 fields") are too generic to prove correctness
        out.append(v)
        if len(out) >= max_n:
            break
    return out


def answer_numbers(contract: Dict[str, Any]) -> List[float]:
    """All numbers visible in the answer: text, KPIs, table rows and chart data."""
    nums: List[float] = []
    texts = [contract.get("spoken_summary") or "", contract.get("display_text") or ""]
    texts += [str(i) for i in contract.get("insights") or []]
    for t in texts:
        nums += [v for v in (_to_float(x) for x in _NUM_RE.findall(t)) if v is not None]
    vis = contract.get("visual") or {}

    def walk(obj: Any) -> None:
        if isinstance(obj, bool):
            return
        if isinstance(obj, (int, float)):
            nums.append(float(obj))
        elif isinstance(obj, str):
            for x in _NUM_RE.findall(obj):
                v = _to_float(x)
                if v is not None:
                    nums.append(v)
        elif isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj[:400]:
                walk(v)

    walk(vis.get("kpis"))
    walk((vis.get("table") or {}).get("rows"))
    walk((vis.get("chart") or {}).get("data"))
    return nums


def anchor_match(anchors: List[float], nums: List[float], tol: float = 0.015) -> bool:
    for a in anchors:
        for n in nums:
            if a == 0:
                if n == 0:
                    return True
            elif abs(n - a) <= abs(a) * tol or abs(abs(n) - abs(a)) <= abs(a) * tol:
                return True
    return False


class GateEvaluator(FullEvaluator):
    def __init__(self, concurrency: int, progress_path: Path):
        super().__init__(concurrency=concurrency)
        if progress_path.exists():
            progress_path.unlink()
        self.checkpoints = CheckpointManager(filepath=progress_path)
        self.subset = yaml.safe_load(SUBSET_PATH.read_text(encoding="utf-8"))
        self.q_by_id = {q["id"]: q for q in self.questions_yaml}
        self.p_by_id = {p["id"]: p for p in self.paraphrases_yaml}
        self.st_by_idx = {s["idx"]: s for s in self.stress_test_prompts}
        self.contracts: Dict[str, Dict[str, Any]] = {}

    async def _turn(self, suite: str, entry_id: str, query: str, session_id: str, persona: str,
                    expected: Dict[str, Any], key_id: str, is_stress: bool = False,
                    stress_item: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        t0 = time.perf_counter()
        try:
            res = await asyncio.wait_for(
                self.runner.execute_turn_async(query=query, session_id=session_id, persona=persona),
                timeout=TURN_TIMEOUT_S)
            rec = self.score_entry(entry_id=entry_id, contract=res, expected=expected, persona=persona,
                                   is_stress_test=is_stress, stress_item=stress_item)
        except Exception as e:  # scored as a failure (incl. TimeoutError), never hidden
            res = {}
            rec = {"entry_id": entry_id, "overall_pass": False, "schema_valid": False, "refusal_ok": False,
                   "tool_ok": False, "citation_ok": False, "numeric_ok": False,
                   "failure_class": f"Execution Exception: {str(e)[:80]}", "latency_ms": 0.0}
        rec["suite"] = suite
        rec["persona_tested"] = persona
        rec["query"] = query[:160]
        rec["wall_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        # Strict anchor check (answered data entries only)
        meta = self.index_meta.get(key_id, {})
        anchors = headline_anchors(meta.get("headline", "")) if (not is_stress and meta.get("status") == "ANSWERED"
                                                                and meta.get("type", "data") in ("data", "policy_plus_data", "what_if")) else []
        if anchors and res:
            rec["anchors"] = anchors
            rec["anchor_ok"] = anchor_match(anchors, answer_numbers(res))
        else:
            rec["anchor_ok"] = None
        rec["strict_pass"] = bool(rec.get("overall_pass")) and rec["anchor_ok"] is not False
        rec["spoken_full"] = (res.get("spoken_summary") or "")[:400] if res else ""
        rec["visual_type"] = ((res.get("visual") or {}).get("type")) if res else None
        rec["row_count"] = len(((res.get("visual") or {}).get("table") or {}).get("rows") or []) if res else 0
        rec["access_status"] = ((res.get("access") or {}).get("status")) if res else None
        rec["has_query_spec"] = bool(res.get("query_spec")) if res else False
        # B4 metrics: insights / drill-downs per data answer and numeric grounding of the spoken answer
        vis = (res.get("visual") or {}) if res else {}
        rec["is_data_answer"] = bool(res) and vis.get("type") in ("chart", "table", "kpi") and \
            (res.get("access") or {}).get("status") != "refused" and bool((vis.get("table") or {}).get("rows"))
        rec["n_insights_v2"] = len(res.get("insights_v2") or []) if res else 0
        rec["n_drilldowns"] = len(res.get("drilldowns") or []) if res else 0
        if res and rec["has_query_spec"]:
            from app.brain.narrator import grounding_violations
            allowed = set(answer_numbers(res))
            allowed |= {abs(x) for x in allowed}
            for i in res.get("insights_v2") or []:
                for x in _NUM_RE.findall(str(i.get("text", ""))):
                    v = _to_float(x)
                    if v is not None:
                        allowed.add(v)
            rec["ungrounded"] = grounding_violations(res.get("spoken_summary") or "", allowed)
        else:
            rec["ungrounded"] = None
        self.contracts[entry_id] = res
        return rec

    async def run(self) -> Dict[str, Any]:
        sem = asyncio.Semaphore(self.concurrency)
        sub = self.subset

        async def guarded(coro_fn):
            async with sem:
                return await coro_fn()

        tasks = []
        for qid in sub["roots"]:
            q = self.q_by_id[qid]
            persona = "E2_HR" if qid in ("D1", "D2", "D3", "D4", "D5", "D6", "P18", "P19", "M3", "M4") else ("DIR_HR" if qid == "P20" else "CMD")
            tasks.append(guarded(lambda q=q, persona=persona: self._turn(
                "root", q["id"], q["question"], f"gate-root-{q['id']}", persona,
                self.expected_root.get(q["id"], {}), q["id"])))
        for qid in sub["paraphrases"]:
            p = self.p_by_id[qid]
            for style in ("formal", "casual", "hinglish"):
                if p.get(style):
                    pid = f"{qid}__{style}"
                    tasks.append(guarded(lambda p=p, style=style, pid=pid: self._turn(
                        "paraphrase", pid, p[style], f"gate-para-{pid}", "CMD",
                        self.expected_root.get(p["id"], {}), p["id"])))
        for idx in sub["stress_idx"]:
            st = self.st_by_idx[idx]
            tasks.append(guarded(lambda st=st: self._turn(
                "stress", f"ST-{st['idx']}", st["prompt"], f"gate-st-{st['idx']}", st["persona"],
                {"row_count": st["rows"]}, f"ST-{st['idx']}", is_stress=True, stress_item=st)))

        async def chain(qid: str) -> List[Dict[str, Any]]:
            q = self.q_by_id[qid]
            sess = f"gate-fu-{qid}"
            out = []
            async with sem:
                try:
                    await asyncio.wait_for(self.runner.execute_turn_async(q["question"], session_id=sess, persona="CMD"),
                                           timeout=TURN_TIMEOUT_S)
                except Exception:
                    pass
            for fu in q.get("followups", []):
                fuid = f"{qid}__{fu['kind']}"
                async with sem:
                    out.append(await self._turn("followup", fuid, fu["question"], sess, "CMD",
                                                self.expected_fu.get(fuid, {}), fuid))
            return out

        t0 = time.perf_counter()
        flat = await asyncio.gather(*tasks)
        chains = await asyncio.gather(*[chain(c) for c in sub["followup_chains"]])
        for c in chains:
            flat.extend(c)
        elapsed = round(time.perf_counter() - t0, 1)
        return {"records": flat, "elapsed_s": elapsed}


def summarize(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for suite in ("root", "followup", "paraphrase", "stress", "all"):
        items = records if suite == "all" else [r for r in records if r.get("suite") == suite]
        if not items:
            continue
        n = len(items)
        lats = sorted(r.get("latency_ms") or 0 for r in items if (r.get("latency_ms") or 0) > 0)
        anchored = [r for r in items if r.get("anchor_ok") is not None]
        out[suite] = {
            "total": n,
            "lenient_pass": sum(1 for r in items if r.get("overall_pass")),
            "strict_pass": sum(1 for r in items if r.get("strict_pass")),
            "lenient_pct": round(100.0 * sum(1 for r in items if r.get("overall_pass")) / n, 1),
            "strict_pct": round(100.0 * sum(1 for r in items if r.get("strict_pass")) / n, 1),
            "anchor_checked": len(anchored),
            "anchor_ok": sum(1 for r in anchored if r.get("anchor_ok")),
            "refusal_ok": sum(1 for r in items if r.get("refusal_ok")),
            "schema_ok": sum(1 for r in items if r.get("schema_valid")),
            "exceptions": sum(1 for r in items if str(r.get("failure_class") or "").startswith("Execution Exception")),
            "data_answers": sum(1 for r in items if r.get("is_data_answer")),
            "data_with_2plus_insights": sum(1 for r in items if r.get("is_data_answer") and (r.get("n_insights_v2") or 0) >= 2),
            "planner_with_2plus_chips": sum(1 for r in items if r.get("has_query_spec") and (r.get("n_drilldowns") or 0) >= 2),
            "planner_answers": sum(1 for r in items if r.get("has_query_spec")),
            "ungrounded_answers": sum(1 for r in items if r.get("ungrounded")),
            "p50_ms": round(lats[len(lats) // 2], 0) if lats else 0,
            "p95_ms": round(lats[int(len(lats) * 0.95)], 0) if lats else 0,
        }
    return out


def scorecard_md(label: str, summary: Dict[str, Any], meta: Dict[str, Any]) -> str:
    lines = [f"| Suite | Turns | Lenient pass | Strict pass (anchor) | Anchor ok / checked | Refusal ok | Schema ok | Exceptions | p50 ms | p95 ms | Data ans. ≥2 insights | Planner ≥2 chips | Ungrounded |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for suite, s in summary.items():
        lines.append(f"| {suite} | {s['total']} | {s['lenient_pass']} ({s['lenient_pct']}%) | {s['strict_pass']} ({s['strict_pct']}%) | "
                     f"{s['anchor_ok']}/{s['anchor_checked']} | {s['refusal_ok']} | {s['schema_ok']} | {s['exceptions']} | {s['p50_ms']} | {s['p95_ms']} | "
                     f"{s['data_with_2plus_insights']}/{s['data_answers']} | {s['planner_with_2plus_chips']}/{s['planner_answers']} | {s['ungrounded_answers']} |")
    head = (f"**Gate:** {label} · **Run:** {meta['timestamp']} · **Model:** {meta['model']} · "
            f"**Flags:** YUKTI_PLANNER={meta['planner']} · cache OFF · **Wall time:** {meta['elapsed_s']} s")
    return head + "\n\n" + "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--out-dir", default=str(EVAL_DIR / "gates"))
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ev = GateEvaluator(concurrency=args.concurrency, progress_path=out_dir / f"{args.label}.progress.jsonl")
    res = asyncio.run(ev.run())
    summary = summarize(res["records"])
    meta = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "model": ev.model_name,
        "planner": os.getenv("YUKTI_PLANNER", "0"),
        "elapsed_s": res["elapsed_s"],
        "subset_version": ev.subset.get("version"),
    }
    payload = {"label": args.label, "meta": meta, "summary": summary, "records": res["records"]}
    (out_dir / f"{args.label}.json").write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    print(scorecard_md(args.label, summary, meta))


if __name__ == "__main__":
    main()
