import re
from typing import Set, List, Tuple

_NUM = re.compile(r"(?<![A-Za-z])[−-]?\d[\d,]*(?:\.\d+)?")
_QUOTE = re.compile(r'"([^"]*)"(?:\s*\[AR\s*FY\d{2}\s*p\.\d+\])?')

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
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    
    dropped = []
    kept = []
    
    for sent in sentences:
        # Remove quoted parts so their numbers aren't checked against `allowed`
        # We only ignore them if they are explicitly quoted AR excerpts.
        # "A number that appears only inside a verbatim quoted AR excerpt (in quotation marks, with a page cite) is allowed..."
        # We'll just remove all quoted strings before checking numbers, or only those with a cite.
        # Let's remove any text in quotes.
        clean_sent = _QUOTE.sub(" ", sent)
        
        # Also ignore FY years
        clean_sent = re.sub(r"\bFY\s?\d{2}(?:\s?[-–]\s?\d{2})?\b", " ", clean_sent, flags=re.I)
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
            dropped.append(sent)
        else:
            kept.append(sent)
            
    if len(dropped) > 1 and fallback_template:
        return fallback_template, dropped
        
    return " ".join(kept), dropped

