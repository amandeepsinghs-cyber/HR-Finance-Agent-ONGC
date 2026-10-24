import re
from typing import Set, List, Tuple

_NUM = re.compile(r"(?<![A-Za-z])[−-]?\d[\d,]*(?:\.\d+)?")
_QUOTE = re.compile(r'"([^"]*)"\s*\[AR\s*FY\d{2}(?:\s+PDF)?\s*p\.[^\]]+\]')

def _to_float(tok: str) -> float | None:
    try:
        return float(tok.replace(",", "").replace("−", "-"))
    except ValueError:
        return None

def check_numeric_grounding(text: str, allowed: Set[float], fallback_template: str = "") -> Tuple[str, List[str]]:
    """
    Checks each sentence in text.
    Numbers inside "..." [AR FYxx p.YY] are ignored (treated as quotes).
    Other numbers must be in `allowed` (with a small tolerance).
    Sentences with ungrounded numbers are dropped.
    Returns (cleaned_text, dropped_sentences).
    If >1 sentence is dropped, returns fallback_template.
    """
    quotes = []
    def _save_quote(m):
        quotes.append(m.group(0))
        return f" __QUOTE_{len(quotes)-1}__ "
        
    text_safe = _QUOTE.sub(_save_quote, text)
    
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text_safe) if s.strip()]
    
    dropped = []
    kept = []
    
    for sent in sentences:
        # Also ignore FY years
        clean_sent = re.sub(r"\bFY\s?\d{2}(?:\s?[-–]\s?\d{2})?\b", " ", sent, flags=re.I)
        # Also calendar years between 1990 and 2040
        
        ungrounded = False
        for match in _NUM.finditer(clean_sent):
            tok = match.group()
            val = _to_float(tok)
            if val is None:
                continue
            if 1990 <= abs(val) <= 2040 and float(val).is_integer() and "," not in tok:
                continue
            # small integers
            if abs(val) < 10 and float(val).is_integer():
                continue
                
            # check allowed
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
            import logging; logging.getLogger(__name__).info(f"grounding_drop: {sent}"); dropped.append(sent)
        else:
            kept.append(sent)
            
    if len(dropped) > 1 and fallback_template:
        return fallback_template, dropped
        
    kept_text = " ".join(kept)
    for i, q in enumerate(quotes):
        kept_text = kept_text.replace(f"__QUOTE_{i}__", q)
        
    return kept_text, dropped

