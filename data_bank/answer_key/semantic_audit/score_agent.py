"""Independent scorer for Yukti agent runs against the frozen answer key (semantic audit 2026-10-20).

Read-only on yukti code. Scores any progress.jsonl (official eval, 120-char evidence) or a full-contract capture
(semantic_audit/capture_contracts.py) and writes per-entry verdicts + rationale + suite summary.

Usage (from data_bank/answer_key):
    uv run python -m semantic_audit.score_agent --run <progress.jsonl|contracts.jsonl> --out <dir> [--no-judge] [--no-sql]

Verdict per entry: PASS | FAIL | (stress) ANSWERED / HONEST_GAP / WRONG ; reason codes explain why.
Deterministic checks first; the Gemini judge (temperature 0) is called only when the deterministic outcome is
UNCERTAIN, and its rationale is stored.

Rules (lead brief 2026-10-20):
- numeric: the key's headline number(s) (from the rendered narrative headline / key rows) must appear in the agent's
  spoken/display text or its table rows (or in the rows its generated SQL returns), +-0.5% or rounding; period must
  match (e.g. FY27-YTD vs FY26).
- entity/period: right entity set and fiscal period.
- policy: right document + clause body (clause number / quoted provision), not just a header.
- refusal: correct per persona (yukti access matrix mirrored below) with a permitted alternative.
- gap entries: honest caveat passes; invented numbers fail.
- "no data" on answerable entries fails.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from semantic_audit import common as C

STRESS_PATH = C.DATA_BANK_DIR / "reports" / "stress_test.md"
PARAS_PATH = C.AK_DIR / "paraphrases.yaml"

# Mirrors yukti/backend/app/access_control.py restricted_personas (read 2026-10-20). CMD is refused only D1/M3 root+why.
RESTRICTED = {
    "D1": {"E2_HR", "E3_FIN", "DIR_HR", "DIR_FIN"}, "M3": {"E2_HR", "E3_FIN", "DIR_HR", "DIR_FIN"},
    "D2": {"E2_HR", "E3_FIN"}, "D3": {"E2_HR", "E3_FIN"}, "D4": {"E2_HR", "E3_FIN"}, "D5": {"E2_HR", "E3_FIN"},
    "D6": {"E2_HR", "E3_FIN"}, "P18": {"E2_HR", "E3_FIN"}, "P19": {"E2_HR", "E3_FIN"},
    "P20": {"DIR_HR", "E2_HR", "E3_FIN"}, "M4": {"E2_HR", "E3_FIN"},
}

NO_DATA = re.compile(r"data not available|not available|couldn'?t find|could not (find|retrieve)|unable to|no (verified )?data|"
                     r"won'?t guess|i apologi[sz]e|there seems to be an issue|cannot (find|answer|retrieve)|do not have (the )?data|"
                     r"not (present|recorded) in the data", re.I)
CAVEAT = re.compile(r"not available|no data|not (recorded|captured|present|in the data)|cannot|can'?t|unable|won'?t guess|closest|"
                    r"proxy|gap|does not (contain|record|exist)|isn'?t (recorded|available)|no (such|record)", re.I)
FY_RE = re.compile(r"\bFY\s?'?(\d{2})\b", re.I)
NUM_RE = re.compile(r"(?<![A-Za-z\d.\-])[-−]?\d[\d,]*(?:\.\d+)?")


# --------------------------------------------------------------------------------------------- helpers
class Num(float):
    """float that remembers how many decimals were written in the source text."""
    dp: int = 0


def parse_num(tok: str) -> Optional[float]:
    t = tok.replace(",", "").replace("−", "-")
    try:
        n = Num(float(t))
    except ValueError:
        return None
    n.dp = len(t.split(".")[1]) if "." in t else 0
    return n


def numbers_in(text: str) -> List[float]:
    out = []
    for m in NUM_RE.finditer(text or ""):
        v = parse_num(m.group(0))
        if v is None:
            continue
        # scale words directly after the number
        tail = (text[m.end():m.end() + 12] or "").lower()
        out.append(v)
        if re.match(r"\s*(lakh crore|lakh-crore)", tail):
            out.append(v * 1e5)
        elif re.match(r"\s*(million|mn)\b", tail):
            out.append(v * 1e6)
        elif re.match(r"\s*(billion|bn)\b", tail):
            out.append(v * 1e9)
    return out


def is_dateish(v: float, ctx: str) -> bool:
    return (1990 <= v <= 2040 and float(v).is_integer())


def _dp(x: float) -> int:
    if isinstance(x, Num):
        return x.dp
    t = repr(float(x))
    if "e" in t or t.endswith(".0"):
        return 0
    return min(len(t.split(".")[1]), 6)


def close(a: float, b: float) -> bool:
    """a = agent value, b = key value. +-0.5% relative, or a equals b rounded to a's own precision (<= 2 dp)."""
    if b == 0:
        return abs(a) < 1e-9
    if abs(a - b) <= abs(b) * 0.005:
        return True
    dp = _dp(a)
    return dp <= 2 and round(b, dp) == a


def as_obj(v):
    """progress/contract fields may be dicts or python-repr strings."""
    if isinstance(v, (dict, list)) or v is None:
        return v
    if isinstance(v, str) and v[:1] in "{[":
        for loader in (json.loads, ast.literal_eval):
            try:
                return loader(v)
            except Exception:  # noqa: BLE001
                pass
    return v


def flatten_numbers(rows: List[Dict[str, Any]], limit: int = 400) -> List[float]:
    vals = []
    for r in rows[:limit]:
        for v in (r.values() if isinstance(r, dict) else r):
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                vals.append(float(v))
            elif isinstance(v, str):
                vals.extend(numbers_in(v))
    return vals


def flatten_strings(rows: List[Dict[str, Any]], limit: int = 400) -> str:
    out = []
    for r in rows[:limit]:
        for v in (r.values() if isinstance(r, dict) else r):
            if isinstance(v, str):
                out.append(v)
    return " | ".join(out)


# --------------------------------------------------------------------------------------------- key
class Key:
    def __init__(self):
        self.qm = C.question_map()
        self.paras = {p["id"]: p for p in yaml.safe_load(PARAS_PATH.read_text(encoding="utf-8"))["paraphrases"]}
        self.changes = {}
        for p in sorted(C.AUDIT_DIR.glob("changes_*.yaml")):
            for c in yaml.safe_load(p.read_text(encoding="utf-8")) or []:
                self.changes[str(c.get("id"))] = c
        self.stress = self._load_stress()

    def _load_stress(self):
        out = {}
        for line in STRESS_PATH.read_text(encoding="utf-8").splitlines():
            if line.startswith("| ") and not line.startswith("| #") and not line.startswith("|---"):
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 8 and parts[0].isdigit():
                    st = "GAP" if "GAP" in parts[4] else ("PARTIAL" if "PARTIAL" in parts[4] else "ANSWERABLE")
                    out[f"ST-{parts[0]}"] = {"persona": parts[1], "prompt": parts[2], "status": st,
                                             "rows": int(parts[5]) if parts[5].isdigit() else 0,
                                             "sql": parts[7], "summary": parts[8] if len(parts) > 8 else ""}
        return out

    def key_id(self, eid: str) -> Optional[str]:
        if eid.startswith("ST-"):
            return None
        root, _, kind = eid.partition("__")
        if kind in ("formal", "casual", "hinglish"):
            return root
        return eid if eid in self.qm else None

    def question(self, eid: str) -> str:
        root, _, kind = eid.partition("__")
        if kind in ("formal", "casual", "hinglish"):
            return self.paras.get(root, {}).get(kind) or self.qm[root]["question"]
        if eid.startswith("ST-"):
            return self.stress.get(eid, {}).get("prompt", "")
        return self.qm.get(eid, {}).get("question", "")

    def facts(self, kid: str) -> Dict[str, Any]:
        res = C.load_json(kid)
        md = C.md_path(kid).read_text(encoding="utf-8")
        sql = C.clean_sql(C.sql_path(kid).read_text(encoding="utf-8"))
        q = self.qm[kid]
        head = C.headline_from_md(md)
        synth = ""
        m = re.search(r"## Executive Synthesis[^\n]*\n(.+?)(?:\n\n|\n#|$)", md, re.S)
        if m:
            synth = m.group(1).strip()
        rows = res.get("rows", [])
        qtext = q["question"]
        qnums = set(numbers_in(qtext))
        # headline numbers: from headline sentence, excluding years/dates/question thresholds/clause refs
        hn = []
        for mm in NUM_RE.finditer(head):
            v = parse_num(mm.group(0))
            if v is None or is_dateish(v, head):
                continue
            pre = head[max(0, mm.start() - 12):mm.start()].lower()
            if re.search(r"(clause|rule|section|part|cl\.|fy|e)\s*$", pre):
                continue
            if v in qnums:
                continue
            hn.append(v)
        rnums = set(flatten_numbers(rows))
        hn_grounded = [v for v in hn if any(close(v, r) or close(v * 1.0, r) for r in rnums)] or hn
        kfy = set(FY_RE.findall(sql)) | set(FY_RE.findall(head))
        is_policy = bool(rows) and ("quote_snippet" in rows[0] or "clause_ref" in rows[0])
        clauses = set()
        docs = set()
        if is_policy:
            for r in rows[:6]:
                docs.add(str(r.get("doc_id", "")))
                for fld in ("provision", "clause_ref", "quote_snippet"):
                    clauses |= {c for c in re.findall(r"\b\d{1,2}\.\d{1,2}(?:\([a-z0-9]+\))?", str(r.get(fld, ""))[:200])
                                if not re.fullmatch(r"\d{1,2}\.0", c)}
        ch = self.changes.get(kid, {})
        gap_tag = "GAP" in (ch.get("defect_class") or [])
        # GAP tags in the change log are often partial (e.g. one sub-part missing); only treat the entry as a gap when
        # the key's own headline says the main ask cannot be answered.
        gap = gap_tag and bool(re.search(r"cannot|can't|not (available|recorded|captured|present|possible|measurable)|no (data|record|quarterly|such|policy|clause|rule)|"
                                         r"does not (exist|record|contain)|isn't (recorded|available)|data gap|not in the (data|corpus)|premise", head, re.I))
        ents = set()
        for r in rows[:15]:
            for k, v in r.items():
                if isinstance(v, str) and 3 < len(v) < 50 and not re.match(r"^(WC|FLD|DISC|EMP|PRJ|E\d)", v) and v.lower() in head.lower():
                    ents.add(v)
        refusal_key = "Executive Determination: REFUSAL" in md
        if refusal_key:
            synth = md.split("## Executive Determination: REFUSAL", 1)[1][:1500]
        return {"kid": kid, "refusal_key": refusal_key, "headline": head, "synthesis": synth, "headline_numbers": hn_grounded[:4], "key_rows": rows,
                "key_fy": kfy, "is_policy": is_policy, "docs": docs - {""}, "clauses": clauses, "gap": gap,
                "entities": ents, "status": "REFUSAL" if q["type"] == "refusal" else "ANSWER", "qtype": q["type"]}


def expected_refusal(eid: str, persona: str) -> bool:
    root, _, kind = eid.partition("__")
    if root not in RESTRICTED:
        return False
    if persona in RESTRICTED[root]:
        return kind in ("", "why", "formal", "casual", "hinglish")
    if persona == "CMD" and root in ("D1", "M3"):
        # individual pay/APAR of a named officer is confidential for every persona (root, why and paraphrases)
        return kind in ("", "why", "formal", "casual", "hinglish")
    return False


# --------------------------------------------------------------------------------------------- agent evidence
class SqlRunner:
    def __init__(self, cache_path: Path, enabled: bool):
        self.cache_path = cache_path
        self.enabled = enabled
        self.cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}

    def rows(self, sql: Optional[str]) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        if not sql or not isinstance(sql, str) or sql.strip() in ("", "None"):
            return None, None
        s = sql.strip().rstrip(";")
        if not re.match(r"(?is)^\s*(with|select)\b", s) or re.search(r"(?i)\b(insert|update|delete|merge|create|drop|alter|truncate)\b", s):
            return None, "non-SELECT SQL not executed"
        h = hashlib.sha1(s.encode()).hexdigest()
        if h in self.cache:
            c = self.cache[h]
            return c.get("rows"), c.get("error")
        if not self.enabled:
            return None, None
        try:
            from google.cloud import bigquery
            cfg = bigquery.QueryJobConfig(default_dataset=f"{C.PROJECT_ID}.hrfin_silver", labels=C.JOB_LABELS,
                                          maximum_bytes_billed=5 * 1024 ** 3)
            job = C.client().query(s, job_config=cfg)
            rs = [{k: C._ser(v) for k, v in r.items()} for r in job.result(max_results=500, timeout=120)]
            self.cache[h] = {"rows": rs, "error": None}
        except Exception as e:  # noqa: BLE001
            self.cache[h] = {"rows": None, "error": str(e)[:300]}
        return self.cache[h]["rows"], self.cache[h]["error"]

    def save(self):
        self.cache_path.write_text(json.dumps(self.cache, default=str))


def evidence(rec: Dict[str, Any], sqlr: SqlRunner) -> Dict[str, Any]:
    spoken = str(rec.get("spoken_summary") or "")
    display = str(rec.get("display_text") or "")
    visual = as_obj(rec.get("visual")) or {}
    sources = as_obj(rec.get("sources")) or []
    access = as_obj(rec.get("access")) or {}
    insights = as_obj(rec.get("insights")) or []
    rows: List[Dict[str, Any]] = []
    vtype = visual.get("type") if isinstance(visual, dict) else None
    if isinstance(visual, dict):
        tbl = visual.get("table") or {}
        if isinstance(tbl, dict):
            cols = tbl.get("columns") or []
            for r in tbl.get("rows") or []:
                if isinstance(r, dict):
                    rows.append(r)
                elif isinstance(r, list):
                    rows.append({str(cols[i].get("key", i)) if i < len(cols) and isinstance(cols[i], dict) else str(i): v for i, v in enumerate(r)})
        for k in ("kpis", "kpi", "chart", "clause", "document", "refusal"):
            if visual.get(k):
                rows.append({"_visual_" + k: json.dumps(visual.get(k), default=str)})
    sql_rows, sql_err = (None, None)
    if not rows:
        sql_rows, sql_err = sqlr.rows(rec.get("generated_sql"))
    text = " ".join([spoken, display, " ".join(map(str, insights)) if isinstance(insights, list) else str(insights)])
    src_text = json.dumps(sources, default=str)
    full = "display_text" in rec
    refused = None
    if isinstance(access, dict) and access.get("status"):
        refused = access.get("status") == "refused" or vtype == "refusal"
    elif "refusal_ok" in rec:
        refused = None  # derive later from refusal_ok + expectation
    return {"text": text, "spoken": spoken, "rows": rows, "sql_rows": sql_rows or [], "sql_err": sql_err,
            "sources": src_text, "vtype": vtype, "full": full, "refused": refused,
            "tool": rec.get("tool_called"), "sql": rec.get("generated_sql"), "error": rec.get("error")}


# --------------------------------------------------------------------------------------------- judge
class Judge:
    def __init__(self, enabled: bool, cache_path: Path, model: str = "gemini-2.5-pro"):
        self.enabled = enabled
        self.model = model
        self.cache_path = cache_path
        self.cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
        self._client = None

    def _c(self):
        """Vertex AI REST via google-auth (no extra dependency in data_bank)."""
        if self._client is None:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession
            creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            self._client = AuthorizedSession(creds)
        return self._client

    def _generate(self, prompt: str) -> str:
        url = (f"https://aiplatform.googleapis.com/v1/projects/{C.PROJECT_ID}/locations/global/publishers/google/"
               f"models/{self.model}:generateContent")
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
                "labels": dict(C.JOB_LABELS)}
        for attempt in range(4):
            r = self._c().post(url, json=body, timeout=180)
            if r.status_code == 429 or r.status_code >= 500:
                import time
                time.sleep(4 * (attempt + 1))
                continue
            r.raise_for_status()
            parts = r.json()["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts if not p.get("thought"))
        r.raise_for_status()
        return ""

    def ask(self, eid: str, question: str, key_desc: str, agent_desc: str) -> Tuple[str, str]:
        prompt = (
            "You are a strict grader of an enterprise analytics agent for ONGC (Indian FY = Apr-Mar; today = 2026-10-19; "
            "FY27 is year-to-date). Compare the AGENT ANSWER to the ANSWER KEY for the QUESTION. Grade PASS only if the agent "
            "gives the key's main finding (same headline number(s) within +-0.5% or simple rounding of the key value - e.g. 6.5 vs a "
            "key of 6.40 is WRONG - same entity set, same fiscal period, or for "
            "policy questions the same document AND the substantive clause provision). 'Data not available' on an answerable "
            "question is FAIL. If the key marks a data GAP, an honest caveat is PASS and invented numbers are FAIL. If the agent "
            "evidence is truncated and what is visible is consistent with the key but the main finding is cut off, answer "
            "INSUFFICIENT (not PASS). Company anchors: headcount 23,117 at 31-Mar-2026 and 22,798 today; FY26 revenue Rs 1,32,508 cr; "
            "FY26 trade receivables outstanding Rs 13,168 cr. "
            'Reply with JSON only: {"verdict": "PASS"|"FAIL"|"INSUFFICIENT", "rationale": "<= 40 words"}.\n\n'
            f"QUESTION: {question}\n\nANSWER KEY: {key_desc[:3000]}\n\nAGENT ANSWER: {agent_desc[:3500]}")
        h = hashlib.sha1((self.model + prompt).encode()).hexdigest()
        if h in self.cache:
            return self.cache[h]["verdict"], self.cache[h]["rationale"]
        if not self.enabled:
            return "UNCERTAIN", "judge disabled"
        try:
            txt = self._generate(prompt)
            d = json.loads(txt[txt.find("{"):txt.rfind("}") + 1])
            v, why = str(d.get("verdict", "FAIL")).upper(), str(d.get("rationale", ""))[:300]
        except Exception as e:  # noqa: BLE001
            v, why = "UNCERTAIN", f"judge error: {str(e)[:150]}"
        if v != "UNCERTAIN":
            self.cache[h] = {"verdict": v, "rationale": why, "eid": eid}
        return v, why

    def save(self):
        self.cache_path.write_text(json.dumps(self.cache, indent=0))


# --------------------------------------------------------------------------------------------- scoring
def _jflags(v: str) -> List[str]:
    return {"UNCERTAIN": ["JUDGE_UNAVAILABLE"], "INSUFFICIENT": ["INSUFFICIENT_EVIDENCE"]}.get(v, [])


def has_number(target: float, text_nums: List[float], row_nums: List[float]) -> Optional[str]:
    for a in text_nums:
        if close(a, target):
            return "text"
    if abs(target) < 10 and float(target).is_integer():
        return None  # small integers coincide too easily with unrelated table cells
    for a in row_nums:
        if close(a, target):
            return "rows"
        for s in (1e7, 1e5, 1e-7, 100.0, 0.01, 1e3, 1e-3, 1e6, 1e-6):  # unitless table cells (₹ vs cr, fraction vs %)
            if close(a * s, target):
                return "rows(scaled)"
    return None


def suite_of(eid: str) -> str:
    if eid.startswith("ST-"):
        return "stress_test"
    k = eid.partition("__")[2]
    if not k:
        return "root"
    return "paraphrases" if k in ("formal", "casual", "hinglish") else "followups"


def score_one(rec, key: Key, sqlr: SqlRunner, judge: Judge) -> Dict[str, Any]:
    eid = rec["entry_id"]
    suite = suite_of(eid)
    persona = rec.get("persona_tested") or ("E2_HR" if eid in RESTRICTED and eid != "P20" else ("DIR_HR" if eid == "P20" else "CMD"))
    ev = evidence(rec, sqlr)
    out = {"entry_id": eid, "suite": suite, "persona": persona, "evidence_level": "full" if ev["full"] else "truncated-120",
           "official_pass": rec.get("overall_pass"), "verdict": None, "reasons": [], "rationale": "", "judge_used": False}
    text_nums = numbers_in(ev["text"])
    row_nums = flatten_numbers(ev["rows"]) + flatten_numbers(ev["sql_rows"])
    all_text = ev["text"] + " " + flatten_strings(ev["rows"]) + " " + flatten_strings(ev["sql_rows"]) + " " + ev["sources"]
    if ev["error"] and ev["error"] != "None":
        out.update(verdict="FAIL", reasons=["EXECUTION_ERROR"], rationale=str(ev["error"])[:200])
        return out

    # ---------------- stress prompts (no frozen key)
    if suite == "stress_test":
        st = key.stress.get(eid, {})
        nodata = bool(NO_DATA.search(ev["spoken"]))
        if st.get("status") == "GAP":
            if nodata or CAVEAT.search(ev["text"]):
                out.update(verdict="HONEST_GAP", reasons=["GAP_CAVEAT"])
            else:
                out.update(verdict="WRONG", reasons=["INVENTED_ON_GAP"], rationale="stress_test.md marks GAP; agent asserted an answer without caveat")
            return out
        if nodata and not ev["rows"] and not ev["sql_rows"]:
            out.update(verdict="WRONG", reasons=["NO_DATA_ON_ANSWERABLE"], rationale=f"stress_test.md: {st.get('status')} ({st.get('rows')} rows) but agent said no data")
            return out
        # key numbers from the stress summary's first row dict
        m = re.search(r"\{[^{}]*\}", st.get("summary", ""))
        knums, kents = [], []
        if m:
            try:
                d = ast.literal_eval(m.group(0))
                knums = [float(v) for v in d.values() if isinstance(v, (int, float)) and not isinstance(v, bool)][:3]
                kents = [v for v in d.values() if isinstance(v, str) and len(v) > 2][:2]
            except Exception:  # noqa: BLE001
                pass
        hits = [n for n in knums if has_number(n, text_nums, row_nums)]
        ent_hit = any(e.lower() in all_text.lower() for e in kents)
        if knums and (len(hits) >= max(1, math.ceil(len(knums) / 2)) or (hits and ent_hit)):
            out.update(verdict="ANSWERED", reasons=["MATCHES_STRESS_SQL_RESULT"], rationale=f"matched {hits} / entity={ent_hit}")
            return out
        key_desc = (f"stress_test.md status {st.get('status')}, {st.get('rows')} rows. Reference SQL result (UNAUDITED pre-audit "
                    f"query - it may itself contain grain/unit errors; if it contradicts the company anchors, judge the agent on "
                    f"correctness and relevance instead): {st.get('summary')}")
        v, why = judge.ask(eid, st.get("prompt", ""), key_desc, agent_desc(ev))
        out["judge_used"] = True
        out.update(verdict={"PASS": "ANSWERED", "FAIL": "WRONG"}.get(v, "WRONG"), reasons=["JUDGE"] + _jflags(v), rationale=why)
        return out

    kid = key.key_id(eid)
    if kid is None:
        out.update(verdict="FAIL", reasons=["NO_KEY"])
        return out
    fx = key.facts(kid)
    exp_ref = expected_refusal(eid, persona)

    # ---------------- refusal
    refused = ev["refused"]
    if refused is None and "refusal_ok" in rec:
        # official eval stores only refusal_ok, judged against ITS expectation (run_eval.py: INDEX status REFUSAL, i.e.
        # refusal roots and their __why, or refusal root under E2_HR/E3_FIN). Recover the actual access status from it.
        root_, _, kind_ = eid.partition("__")
        eval_exp = (root_ in RESTRICTED and kind_ in ("", "why")) or (root_ in RESTRICTED and persona in ("E2_HR", "E3_FIN"))
        refused = eval_exp if rec.get("refusal_ok") else (not eval_exp)
    if exp_ref:
        if not refused:
            out.update(verdict="FAIL", reasons=["REFUSAL_MISSING"], rationale=f"{persona} must be refused for {kid}")
            return out
        alt_ok = bool(ev["rows"] or ev["sql_rows"]) or bool(re.search(r"(instead|alternative|can (show|share)|published|pay scale|band|aggregate|ESS|procedure)", ev["text"], re.I))
        if not ev["full"] and not alt_ok:
            alt_ok = None
        if alt_ok is False:
            out.update(verdict="FAIL", reasons=["REFUSAL_WITHOUT_ALTERNATIVE"])
        else:
            out.update(verdict="PASS", reasons=["REFUSED_CORRECTLY"] + (["ALT_UNVERIFIED"] if alt_ok is None else []))
        return out
    if refused and not fx["refusal_key"]:
        out.update(verdict="FAIL", reasons=["UNEXPECTED_REFUSAL"], rationale=f"{persona} is allowed {kid}")
        return out
    if fx["refusal_key"]:
        # key is a refusal card but this persona is allowed (e.g. CMD asking 'why can't I see X'): the answer must
        # explain the restriction with the right rule; judged against the key's justification text.
        kind = eid.partition("__")[2]
        if kind == "why":
            key_desc = (f"The user asks WHY the information is restricted. PASS only if the agent explains the restriction AND "
                        f"cites the governing rule given in the key (document + clause/section). Key: {fx['synthesis']}")
        else:
            key_desc = (f"Persona {persona} IS CLEARED for this information under the access matrix (only E2_HR/E3_FIN-type "
                        f"personas are refused). PASS if the agent gives a substantive, grounded answer (e.g. consistent with the "
                        f"permitted aggregate data in the key, or the requested detail); FAIL if it says data is not available, "
                        f"refuses, or invents unsupported figures. Key (refusal card shown to restricted personas, with the "
                        f"permitted aggregate): {fx['synthesis']} Key rows: {json.dumps(fx['key_rows'][:5], default=str)[:800]}")
        v, why = judge.ask(eid, key.question(eid), key_desc, agent_desc(ev))
        out["judge_used"] = True
        out.update(verdict=v if v in ("PASS", "FAIL") else "FAIL", reasons=["REFUSAL_EXPLANATION", "JUDGE"] + _jflags(v), rationale=why)
        return out

    nodata = bool(NO_DATA.search(ev["spoken"])) and not (ev["rows"] or ev["sql_rows"])
    # ---------------- gap entries
    if fx["gap"]:
        if nodata or CAVEAT.search(ev["text"]):
            # an honest caveat passes unless the agent also asserts numbers contradicting the key
            out.update(verdict="PASS", reasons=["GAP_HONEST_CAVEAT"])
            return out
    elif nodata:
        out.update(verdict="FAIL", reasons=["NO_DATA_ON_ANSWERABLE"], rationale=f"key: {fx['headline'][:160]}")
        return out

    reasons = []
    # ---------------- policy
    if fx["is_policy"]:
        doc_hit = any(d and d.lower() in all_text.lower() for d in fx["docs"]) or any(
            w in all_text.lower() for d in fx["docs"] for w in [d.split("-")[0].lower()] if len(w) > 2)
        cl_hit = [c for c in fx["clauses"] if re.search(rf"(?<![\d.]){re.escape(c)}(?![\d])", all_text)]
        num_hits = [n for n in fx["headline_numbers"] if has_number(n, text_nums, row_nums)]
        if (cl_hit and doc_hit) or (cl_hit and num_hits) or (doc_hit and num_hits and len(num_hits) == len(fx["headline_numbers"]) > 0):
            out.update(verdict="PASS", reasons=["POLICY_DOC_CLAUSE_MATCH"], rationale=f"clauses={cl_hit[:3]} nums={num_hits}")
            return out
        if ev["full"] and not doc_hit and not cl_hit and not num_hits:
            out.update(verdict="FAIL", reasons=["WRONG_POLICY"], rationale=f"expected {sorted(fx['docs'])} {sorted(fx['clauses'])[:4]}")
            return out
        reasons.append("POLICY_UNCERTAIN")
    else:
        # ---------------- numeric + period + entity
        hn = fx["headline_numbers"]
        hits = {n: has_number(n, text_nums, row_nums) for n in hn}
        primary_ok = bool(hn) and bool(hits[hn[0]])
        n_ok = sum(1 for v in hits.values() if v)
        afy = set(FY_RE.findall(str(ev["sql"] or ""))) | set(FY_RE.findall(ev["text"]))
        period_bad = bool(fx["key_fy"]) and bool(afy) and not (afy & fx["key_fy"])
        ent_ok = (not fx["entities"]) or any(e.lower() in all_text.lower() for e in fx["entities"])
        if period_bad:
            out.update(verdict="FAIL", reasons=["WRONG_PERIOD"], rationale=f"key FY{sorted(fx['key_fy'])} vs agent FY{sorted(afy)}")
            return out
        if hn and primary_ok and (n_ok >= math.ceil(len(hn) / 2)) and ent_ok:
            out.update(verdict="PASS", reasons=["HEADLINE_NUMBERS_MATCH"], rationale=f"matched {[(k, v) for k, v in hits.items() if v]}")
            return out
        if hn and ev["full"] and n_ok == 0 and (text_nums or row_nums):
            reasons.append("NUMBERS_DIFFER")
        elif not ent_ok:
            reasons.append("ENTITY_MISMATCH")
        else:
            reasons.append("NUMERIC_UNCERTAIN")

    key_desc = (f"Headline: {fx['synthesis'][:1200]}\nKey rows (first 5): {json.dumps(fx['key_rows'][:5], default=str)[:1500]}"
                + ("\nKEY MARKS THIS AS A DATA GAP (closest honest answer)." if fx["gap"] else ""))
    v, why = judge.ask(eid, key.question(eid), key_desc, agent_desc(ev))
    out["judge_used"] = True
    out.update(verdict=v if v in ("PASS", "FAIL") else "FAIL", reasons=reasons + ["JUDGE"] + _jflags(v), rationale=why)
    return out


def agent_desc(ev) -> str:
    rows = ev["rows"] or ev["sql_rows"]
    src = "table rows" if ev["rows"] else ("rows returned by the agent's generated SQL (re-executed)" if ev["sql_rows"] else "no rows")
    return (f"[evidence: {'full contract' if ev['full'] else 'spoken text truncated to 120 chars by the official eval'}]\n"
            f"Spoken/display: {ev['text'][:1500]}\nTool: {ev['tool']} | SQL: {str(ev['sql'])[:600]}\n"
            f"Sources: {ev['sources'][:400]}\n{src} (first 8): {json.dumps(rows[:8], default=str)[:1500]}"
            + (f"\nSQL error: {ev['sql_err']}" if ev["sql_err"] else ""))


def summarize(verdicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    by = defaultdict(list)
    for v in verdicts:
        by[v["suite"]].append(v)
    summ = {}
    for s, items in by.items():
        n = len(items)
        if s == "stress_test":
            c = Counter(v["verdict"] for v in items)
            summ[s] = {"total": n, **dict(c), "pass_like": c.get("ANSWERED", 0) + c.get("HONEST_GAP", 0),
                       "pass_rate_pct": round((c.get("ANSWERED", 0) + c.get("HONEST_GAP", 0)) * 100 / n, 1),
                       "official_pass": sum(1 for v in items if v["official_pass"]),
                       "judge_used": sum(1 for v in items if v["judge_used"]),
                       "insufficient_evidence": sum(1 for v in items if "INSUFFICIENT_EVIDENCE" in v["reasons"]),
                       "reasons": dict(Counter(v["reasons"][0] for v in items if v["verdict"] == "WRONG"))}
        else:
            p = sum(1 for v in items if v["verdict"] == "PASS")
            summ[s] = {"total": n, "pass": p, "pass_rate_pct": round(p * 100 / n, 1),
                       "official_pass": sum(1 for v in items if v["official_pass"]),
                       "official_pass_but_independent_fail": sum(1 for v in items if v["official_pass"] and v["verdict"] != "PASS"),
                       "judge_used": sum(1 for v in items if v["judge_used"]),
                       "insufficient_evidence": sum(1 for v in items if "INSUFFICIENT_EVIDENCE" in v["reasons"]),
                       "upper_bound_pct": round((p + sum(1 for v in items if "INSUFFICIENT_EVIDENCE" in v["reasons"])) * 100 / n, 1),
                       "reasons": dict(Counter(r for v in items if v["verdict"] != "PASS" for r in v["reasons"][:1]))}
    tot = len(verdicts)
    ok = sum(1 for v in verdicts if v["verdict"] in ("PASS", "ANSWERED", "HONEST_GAP"))
    ins = sum(1 for v in verdicts if "INSUFFICIENT_EVIDENCE" in v["reasons"])
    summ["grand_total"] = {"turns": tot, "pass_like": ok, "pass_rate_pct": round(ok * 100 / tot, 1) if tot else 0,
                           "insufficient_evidence": ins, "upper_bound_pct": round((ok + ins) * 100 / tot, 1) if tot else 0,
                           "official_pass": sum(1 for v in verdicts if v["official_pass"])}
    return summ


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--no-sql", action="store_true")
    ap.add_argument("--judge-model", default="gemini-2.5-pro")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    recs = {}
    for l in Path(a.run).read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            recs[r["entry_id"]] = r  # last record wins (checkpoint semantics)
    key = Key()
    cache_dir = C.AUDIT_DIR / "agent_runs"
    cache_dir.mkdir(exist_ok=True)
    sqlr = SqlRunner(cache_dir / "agent_sql_cache.json", not a.no_sql)
    judge = Judge(not a.no_judge, cache_dir / "judge_cache.json", a.judge_model)
    from concurrent.futures import ThreadPoolExecutor
    # pre-warm SQL cache in parallel
    if not a.no_sql:
        sqls = [r.get("generated_sql") for r in recs.values() if not (as_obj(r.get("visual")) or {}).get("table")]
        with ThreadPoolExecutor(max_workers=12) as ex:
            list(ex.map(sqlr.rows, sqls))
        sqlr.save()
    with ThreadPoolExecutor(max_workers=8) as ex:
        verdicts = list(ex.map(lambda r: score_one(r, key, sqlr, judge), recs.values()))
    sqlr.save()
    judge.save()
    verdicts.sort(key=lambda v: (["root", "followups", "paraphrases", "stress_test"].index(v["suite"]), v["entry_id"]))
    (out / "verdicts.jsonl").write_text("\n".join(json.dumps(v, default=str) for v in verdicts) + "\n", encoding="utf-8")
    summ = summarize(verdicts)
    (out / "summary.json").write_text(json.dumps(summ, indent=2), encoding="utf-8")
    print(json.dumps(summ, indent=2))


if __name__ == "__main__":
    main()
