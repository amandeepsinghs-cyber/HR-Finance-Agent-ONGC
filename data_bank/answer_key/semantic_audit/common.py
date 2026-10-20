"""Shared helpers for the 2026-10-20 semantic audit of the answer key.

Re-executes corrected SQL, rewrites expected JSON, and renders answers/*.md with a
real CMD-style narrative produced *from the result rows* (no typed numbers).

Narratives live in narratives_<group>.py modules as NARRATIVES = {entry_id: fn(rows) -> str}.
"""

from __future__ import annotations

import datetime
import importlib
import json
import pkgutil
import re
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, List

import yaml

PROJECT_ID = "ongc-hr-finance-agent"
LOCATION = "asia-south1"
JOB_LABELS = {"datacloud": "ai-agent"}

AK_DIR = Path(__file__).resolve().parent.parent
DATA_BANK_DIR = AK_DIR.parent
SQL_DIR = AK_DIR / "sql"
EXPECTED_DIR = AK_DIR / "expected"
ANSWERS_DIR = AK_DIR / "answers"
FOLLOWUPS_DIR = AK_DIR / "followups"
QUESTIONS_PATH = DATA_BANK_DIR / "world_bible" / "reference" / "questions.yaml"
AUDIT_DIR = Path(__file__).resolve().parent

GENERIC_MARKER = "indicates operational patterns"

# Sanity anchors (demo 'today' = 2026-10-19; Indian FY = Apr-Mar)
COMPANY_HC_FY26_END = 23117          # headcount_snapshot month 2026-03
COMPANY_HC_TODAY = 22798             # employee_master Active as of 2026-10-19
REVENUE_FY26_CR = 132508             # corporate_financials FY26


# --------------------------------------------------------------------------------------
# Question metadata
# --------------------------------------------------------------------------------------
_QMAP: Dict[str, Dict[str, Any]] | None = None


def question_map() -> Dict[str, Dict[str, Any]]:
    """entry_id -> {question, type, parent, kind}."""
    global _QMAP
    if _QMAP is None:
        data = yaml.safe_load(QUESTIONS_PATH.read_text(encoding="utf-8"))
        m: Dict[str, Dict[str, Any]] = {}
        for q in data["questions"]:
            m[q["id"]] = {"question": q["question"], "type": q.get("type", "data"), "parent": None, "kind": ""}
            for fu in q.get("followups", []):
                fid = f"{q['id']}__{fu['kind']}"
                m[fid] = {"question": fu["question"], "type": q.get("type", "data"), "parent": q["id"], "kind": fu["kind"]}
        _QMAP = m
    return _QMAP


def sql_path(eid: str) -> Path:
    return (FOLLOWUPS_DIR if "__" in eid else SQL_DIR) / f"{eid}.sql"


def json_path(eid: str) -> Path:
    return FOLLOWUPS_DIR / f"{eid}.json" if "__" in eid else EXPECTED_DIR / f"{eid}.json"


def md_path(eid: str) -> Path:
    return FOLLOWUPS_DIR / f"{eid}.md" if "__" in eid else ANSWERS_DIR / f"{eid}.md"


def load_json(eid: str) -> Dict[str, Any]:
    return json.loads(json_path(eid).read_text(encoding="utf-8"))


def clean_sql(text: str) -> str:
    """Same comment stripping as tests/test_51_53_answer_key.py."""
    return "\n".join(l for l in text.splitlines() if not l.strip().startswith("--")).strip()


# --------------------------------------------------------------------------------------
# BigQuery execution (identical result shape to build_answer_key.execute_sql)
# --------------------------------------------------------------------------------------
_CLIENT = None


def client():
    global _CLIENT
    if _CLIENT is None:
        from google.cloud import bigquery
        _CLIENT = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    return _CLIENT


def _ser(v: Any) -> Any:
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def execute_sql(sql: str) -> Dict[str, Any]:
    from google.cloud import bigquery
    t0 = time.time()
    cfg = bigquery.QueryJobConfig(default_dataset=f"{PROJECT_ID}.hrfin_silver", labels=JOB_LABELS, use_query_cache=False)
    job = client().query(sql, job_config=cfg)
    raw = list(job.result())
    cols = list(raw[0].keys()) if raw else [f.name for f in (job.result().schema or [])]
    rows = [{k: _ser(r[k]) for k in cols} for r in raw]
    return {
        "job_id": job.job_id,
        "total_bytes_processed": job.total_bytes_processed or 0,
        "executed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "elapsed_seconds": round(time.time() - t0, 2),
        "row_count": len(rows),
        "columns": cols,
        "rows": rows,
    }


# --------------------------------------------------------------------------------------
# Number formatting helpers for narratives (values always come from result rows)
# --------------------------------------------------------------------------------------
def _indian_group(int_str: str) -> str:
    neg = int_str.startswith("-")
    s = int_str.lstrip("-")
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if neg else "") + s


def num(x: Any, dp: int = 0) -> str:
    """Indian digit grouping: 132508 -> 1,32,508."""
    if x is None:
        return "n/a"
    x = float(x)
    if dp == 0:
        return _indian_group(str(int(round(x))))
    whole, frac = f"{x:.{dp}f}".split(".")
    return _indian_group(whole) + "." + frac


def inr_cr(x: Any, dp: int = 0) -> str:
    return "n/a" if x is None else f"₹{num(x, dp)} cr"


def inr_lakh(x: Any, dp: int = 1) -> str:
    return "n/a" if x is None else f"₹{num(x, dp)} lakh"


def inr(x: Any) -> str:
    return "n/a" if x is None else f"₹{num(x)}"


def pct(x: Any, dp: int = 1) -> str:
    return "n/a" if x is None else f"{float(x):.{dp}f}%"


def signed_pct(x: Any, dp: int = 1) -> str:
    return "n/a" if x is None else f"{float(x):+.{dp}f}%"


def f(x: Any, dp: int = 1) -> str:
    return "n/a" if x is None else f"{float(x):,.{dp}f}"


def names(rows: List[Dict[str, Any]], key: str, n: int = 3) -> str:
    vals = [str(r.get(key)) for r in rows[:n] if r.get(key) is not None]
    if not vals:
        return "none"
    if len(vals) == 1:
        return vals[0]
    return ", ".join(vals[:-1]) + " and " + vals[-1]


def total(rows: List[Dict[str, Any]], key: str) -> float:
    return sum(float(r.get(key) or 0) for r in rows)


# --------------------------------------------------------------------------------------
# Narrative registry
# --------------------------------------------------------------------------------------
def load_narratives() -> Dict[str, Callable[[List[Dict[str, Any]]], str]]:
    reg: Dict[str, Callable] = {}
    import semantic_audit  # noqa: F401  (package import for pkgutil)
    for mod in pkgutil.iter_modules([str(AUDIT_DIR)]):
        if mod.name.startswith("narratives_"):
            m = importlib.import_module(f"semantic_audit.{mod.name}")
            dup = set(reg) & set(m.NARRATIVES)
            if dup:
                raise RuntimeError(f"Duplicate narratives {dup} in {mod.name}")
            reg.update(m.NARRATIVES)
    return reg


def format_table_markdown(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "*No rows returned.*"
    headers = list(rows[0].keys())
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(h, "")) for h in headers) + " |")
    return "\n".join(out)


def render_md(eid: str, res: Dict[str, Any], narrative: str, table_rows: int = 10) -> str:
    q = question_map()[eid]
    lines = [
        f"# Answer Key: {eid}",
        "",
        f"**Question:** {q['question']}",
        f"**Type:** `{q['type']}` | **Result Count:** `{res['row_count']}` rows | **Execution:** `{res['elapsed_seconds']}s`",
        "",
        "## Executive Synthesis",
        narrative.strip(),
        "",
        "### Summary Result Table",
        format_table_markdown(res["rows"][:table_rows]),
    ]
    return "\n".join(lines)


def headline_from_md(text: str) -> str:
    """First sentence of the Executive Synthesis paragraph (for INDEX.md)."""
    m = re.search(r"## Executive Synthesis[^\n]*\n(.+?)(?:\n\n|\n#|$)", text, re.S)
    if not m:
        return ""
    para = m.group(1).strip().replace("\n", " ")
    sent = re.split(r"(?<=[.!?])\s+(?=[A-Z₹])", para)[0]
    return sent.replace("|", "/")[:220]
