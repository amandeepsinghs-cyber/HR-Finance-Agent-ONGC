"""Narrator limited to computed facts + numeric-grounding check (B4.3, FEAT-011).

The spoken answer is assembled from (a) the deterministic headline built by the presenter
from result rows and (b) the computed insights. `grounding_violations()` extracts every
number from the final text and checks it against the numbers the answer is allowed to use
(result cells, insight facts, spec filter values, row counts, fiscal years). Any ungrounded
number makes the narrator fall back to the headline alone, so no invented number reaches
the user. Spoken answers are 2–4 sentences (V8 §4).
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Set

from app.brain.insights import Insight
from app.brain.query_spec import QuerySpec

_NUM = re.compile(r"(?<![A-Za-z])[−-]?\d[\d,]*(?:\.\d+)?")
_SENT = re.compile(r"(?<=[.!?])\s+")
_FY = re.compile(r"\bFY\s?\d{2}(?:\s?[-–]\s?\d{2})?\b", re.I)
_DATE = re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?[\s-][A-Za-z]{3,9}(?:[\s-]\d{4}|\s+FY\d{2})?\b", re.I)
_GRADE = re.compile(r"\b[EW]\d\b|\bW\d[–-]W\d\b")


def _to_float(tok: str) -> Optional[float]:
    try:
        return float(tok.replace(",", "").replace("−", "-"))
    except ValueError:
        return None


def allowed_numbers(rows: List[Dict[str, Any]], insights: List[Insight], spec: Optional[QuerySpec],
                    extra: Iterable[float] = ()) -> Set[float]:
    out: Set[float] = set()

    def add(v: Any):
        if isinstance(v, bool) or v is None:
            return
        if isinstance(v, (int, float)):
            out.add(float(v))
            out.add(abs(float(v)))
        elif isinstance(v, str):
            for t in _NUM.findall(v):
                f = _to_float(t)
                if f is not None:
                    out.add(f)
                    out.add(abs(f))

    for r in rows[:2000]:
        for v in r.values():
            add(v)
    for ins in insights:
        for f in ins.facts:
            add(f)
        add(ins.value)
        add(ins.text)
    if spec is not None:
        for f in spec.filters:
            for v in (f.value if isinstance(f.value, list) else [f.value]):
                add(v)
    for v in extra:
        add(v)
    return out


def _grounded(x: float, allowed: Set[float]) -> bool:
    if abs(x) < 10 and float(x).is_integer():
        return True  # small integers (counts of groups, "top 3", sentence ordinals) are structural
    for a in allowed:
        if a == x:
            return True
        tol = max(abs(a) * 0.006, 0.051 if not float(x).is_integer() else 0.5)
        if abs(abs(a) - abs(x)) <= tol:
            return True
    return False


def grounding_violations(text: str, allowed: Set[float]) -> List[str]:
    t = _FY.sub(" ", text or "")
    t = _DATE.sub(" ", t)
    t = _GRADE.sub(" ", t)
    bad = []
    for tok in _NUM.findall(t):
        x = _to_float(tok)
        if x is None:
            continue
        if 1990 <= abs(x) <= 2040 and float(x).is_integer() and "," not in tok:
            continue  # calendar years
        if not _grounded(x, allowed):
            bad.append(tok)
    return bad


def compose_spoken(headline: str, insights: List[Insight], allowed: Set[float], max_sentences: int = 4) -> Dict[str, Any]:
    """Headline + up to two insight sentences, 2–4 sentences, every number grounded."""
    base = [s.strip() for s in _SENT.split(headline.strip()) if s.strip() and "on screen" not in s.lower()]
    sentences = list(base[: max(1, max_sentences - 2)])
    for ins in insights:
        if len(sentences) >= max_sentences - 1:
            break
        if ins.type in ("headline", "causal_rag"):
            continue  # headline restates value; multi-sentence causal_rag card stays on screen
        ins_sents = [s.strip() for s in _SENT.split((ins.text or "").strip()) if s.strip()]
        if not ins_sents or len(sentences) + len(ins_sents) > max_sentences - 1:
            continue
        if ins.text not in sentences and not any(ins.text[:30] in s for s in sentences):
            sentences.extend(ins_sents)
    sentences = sentences[: max(1, max_sentences - 1)]
    sentences.append("Details are on screen.")
    text = " ".join(s.strip() for s in sentences)
    bad = grounding_violations(text, allowed)
    if bad:  # fall back to the deterministic headline only
        text = " ".join(base[: max(1, max_sentences - 1)] + ["Details are on screen."])
        bad = grounding_violations(text, allowed)
    return {"text": text, "ungrounded": bad, "sentences": len([s for s in _SENT.split(text) if s])}
