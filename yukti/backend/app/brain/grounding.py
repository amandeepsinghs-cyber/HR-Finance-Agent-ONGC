import logging
import re
from typing import List, Set, Tuple

logger = logging.getLogger(__name__)

_NUM = re.compile(r"(?<![A-Za-z])[−-]?\d[\d,]*(?:\.\d+)?")
_QUOTE = re.compile(r'"([^"]*)"\s*\[AR\s*FY\d{2}(?:\s+PDF)?\s*p\.[^\]]+\]')
# SPEC-11 §5: Narrator rejects ungrounded coverage claims unless explicitly from the coverage manifest
_COVERAGE_CLAIM_RE = re.compile(
    r"\b(only|up\s+to|upto|until|not\s+available|don'?t\s+have|do\s+not\s+have|cannot\s+access)\b"
    r".*\b(FY\s?\d{2,4}|20\d\d|data|balance\s+sheet|income\s+statement|cash\s+flow)\b",
    re.I,
)


def _to_float(tok: str) -> float | None:
    try:
        return float(tok.replace(",", "").replace("−", "-"))
    except ValueError:
        return None


def check_numeric_grounding(
    text: str,
    allowed: Set[float],
    fallback_template: str = "",
    allow_coverage_claims: bool = False,
) -> Tuple[str, List[str]]:
    """
    Checks each sentence in text.
    Numbers inside "..." [AR FYxx p.YY] are ignored (treated as quotes).
    Other numbers must be in `allowed` (with a small tolerance).
    Sentences with ungrounded numbers or unauthorized coverage claims are dropped.
    Returns (cleaned_text, dropped_sentences).
    If >1 sentence is dropped, returns fallback_template.
    """
    quotes = []

    def _save_quote(m):
        quotes.append(m.group(0))
        return f" __QUOTE_{len(quotes)-1}__ "

    text_safe = _QUOTE.sub(_save_quote, text or "")

    sentences = [s.strip() for s in re.split(r"(?<=[.!?।])\s+", text_safe) if s.strip()]

    dropped = []
    kept = []

    for sent in sentences:
        if not allow_coverage_claims and _COVERAGE_CLAIM_RE.search(sent):
            logger.info(f"grounding_drop: coverage_claim: {sent}")
            dropped.append(sent)
            continue

        # Ignore FY years, grade tokens (E1..E9, W1..W7), and date tokens (e.g. 19-Oct-2026, 31 March)
        clean_sent = re.sub(r"\bFY\s?\d{2}(?:\s?[-–]\s?\d{2})?\b", " ", sent, flags=re.I)
        clean_sent = re.sub(
            r"\b\d{1,2}(?:st|nd|rd|th)?[\s-][A-Za-z]{3,9}(?:[\s-]\d{4}|\s+FY\d{2})?\b",
            " ",
            clean_sent,
            flags=re.I,
        )
        clean_sent = re.sub(r"\b[EW]\d\b|\bW\d[–-]W\d\b", " ", clean_sent)

        ungrounded = False
        for match in _NUM.finditer(clean_sent):
            tok = match.group()
            val = _to_float(tok)
            if val is None:
                continue
            if 1990 <= abs(val) <= 2040 and float(val).is_integer() and "," not in tok:
                continue
            # small structural integers
            if abs(val) < 10 and float(val).is_integer():
                continue

            found = False
            for a in allowed:
                if a == val:
                    found = True
                    break
                tol = max(abs(a) * 0.006, 0.051 if not float(val).is_integer() else 0.5)
                if abs(abs(a) - abs(val)) <= tol:
                    found = True
                    break

            if not found:
                ungrounded = True
                break

        if ungrounded:
            logger.info(f"grounding_drop: {sent}")
            dropped.append(sent)
        else:
            kept.append(sent)

    if len(dropped) > 1 and fallback_template:
        return fallback_template, dropped

    kept_text = " ".join(kept)
    for i, q in enumerate(quotes):
        kept_text = kept_text.replace(f"__QUOTE_{i}__", q)

    return kept_text, dropped
