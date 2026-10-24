"""Query normalisation for Yukti AI (B1.3).

1. **Fiscal-year resolver** (decision D-30): the demo anchor date is 19-Oct-2026, so
   the current FY is FY27 (Apr-2026 .. Mar-2027, in progress).
   - "this year" / "current year" / "is saal" / "latest" -> FY26 (the latest complete FY).
   - "last year" / "previous year" / "pichle saal" / "last fiscal" -> FY25 (the year before the latest complete FY26). "year before last" -> FY24.
   - "last N years" -> the N complete FYs ending FY26 (e.g. 5 -> FY22..FY26).
   - Explicit "FY25", "FY 2024-25", "2024-25", "FY2025" -> FY25.
2. **Case-insensitive categorical filters:** generated SQL often writes a filter
   value in the wrong case (e.g. `employment_status = 'active'` while the data
   stores 'Active'), which silently returns 0 rows. Using the profiled values in
   `semantic_catalog.json`, literals are rewritten to the exact stored spelling;
   where joined tables disagree on the spelling, the comparison becomes
   `LOWER(col) = 'value'`.
"""

import datetime
from functools import lru_cache
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Optional, Set

logger = logging.getLogger("yukti.semantic.normalize")

CATALOG_PATH = Path(__file__).resolve().parent / "semantic_catalog.json"
ANCHOR_DATE = datetime.date(2026, 10, 19)


# --------------------------------------------------------------------------- FY
def fy_of(d: datetime.date) -> int:
    """Indian fiscal year number (FY27 = Apr-2026 .. Mar-2027) as an int, e.g. 27."""
    return (d.year + 1 if d.month >= 4 else d.year) % 100


def fy_label(n: int) -> str:
    return f"FY{n % 100:02d}"


def current_fy(anchor: datetime.date = ANCHOR_DATE) -> str:
    return fy_label(fy_of(anchor))


def last_complete_fy(anchor: datetime.date = ANCHOR_DATE) -> str:
    return fy_label(fy_of(anchor) - 1)


_WORD_NUM = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
             "do": 2, "teen": 3, "char": 4, "paanch": 5, "panch": 5}


def resolve_fy(text: str, available: Optional[Iterable[str]] = None,
               anchor: datetime.date = ANCHOR_DATE) -> Optional[Dict[str, Any]]:
    """Resolves a time phrase to {'fy': 'FY26'} or {'from': 'FY22', 'to': 'FY26', 'n_years': 5}.

    `available` = FY labels present in the target table; used only for "this year".
    Returns None when the text has no time reference.
    """
    t = (text or "").lower()
    # Strip planner contexts in parentheses (e.g. "(context: latest FY26)") so they don't override the actual question intent.
    t = re.sub(r"\(context:[^)]+\)", "", t)
    cur = fy_of(anchor)
    last = cur - 1
    avail = sorted({a.upper() for a in available}) if available else []

    # Explicit FY range ("from FY17 to FY26", "FY17-FY26", "from 2017 to 2026")
    m = re.search(r"\b(?:from\s+|between\s+)?(?:fy\s?'?)?(201[7-9]|202[0-7]|1[7-9]|2[0-7])\s*(?:to|and|through|[-–])\s*(?:fy\s?'?)?(201[7-9]|202[0-7]|1[7-9]|2[0-7])\b", t)
    # P0.2 (BUG-20): "FY 2024-25" / "FY2024–25" / "FY24-25" name ONE Indian FY (by its end year): adjacent years
    # joined only by a dash, with no "FY" on the right-hand side and no range word, are not a range.
    if m and not re.search(r"\b(?:to|and|through|from|between)\b", m.group(0)) \
            and not re.search(r"[-–]\s*fy", m.group(0)) \
            and int(m.group(2)) % 100 == (int(m.group(1)) + 1) % 100:
        m = None
    if m and ("fy" in m.group(0) or "to" in m.group(0) or "from" in m.group(0) or int(m.group(2)) % 100 > (int(m.group(1)) % 100) + 1):
        lo_n, hi_n = int(m.group(1)) % 100, int(m.group(2)) % 100
        if 17 <= lo_n <= hi_n <= 27:
            return {"from": fy_label(lo_n), "to": fy_label(hi_n), "n_years": hi_n - lo_n + 1}

    # Explicit FY labels / year ranges ("FY 2024-25", "FY24-25" and "2024-25" name the FY by its end year)
    for m in re.finditer(r"(?:(?<=fy)|\b)(20\d{2})\s?[-–/]\s?(\d{2}|20\d{2})\b", t):  # P0.2: also "fy2024-25"
        if int(m.group(2)) % 100 == (int(m.group(1)) + 1) % 100:  # not a date like 2026-10-19
            return {"fy": fy_label(int(m.group(2)))}
    for m in re.finditer(r"\bfy\s?'?(\d{2})\s?[-–/]\s?(\d{2})\b", t):
        if int(m.group(2)) % 100 == (int(m.group(1)) + 1) % 100:
            return {"fy": fy_label(int(m.group(2)))}
    fy_hits = [int(x) % 100 for x in re.findall(r"\bfy\s?'?(20\d{2}|\d{2})(?!\d)", t) if 17 <= int(x) % 100 <= 27]
    if len(set(fy_hits)) >= 2:
        lo_f, hi_f = min(fy_hits), max(fy_hits)
        if hi_f - lo_f == 1 and re.search(r"\b(compared\s+to|vs\.?|versus|against|from\s+prior)\b", t):
            return {"fy": fy_label(hi_f)}
        return {"from": fy_label(lo_f), "to": fy_label(hi_f), "n_years": hi_f - lo_f + 1}
    if fy_hits:
        return {"fy": fy_label(fy_hits[0])}

    # Ranges: "last 5 years", "past three years", "10-year", "10 year trend", "pichle 5 saal", "over 5 years"
    m = re.search(r"\b(?:(?:over|in|during) the (?:last|past)|last|past|previous|pichle|pichhle)\s+(\d+|[a-z]+)\s+(?:fiscal\s+)?(?:years?|yrs?|saal|varsh)\b", t)
    if not m:
        m = re.search(r"\b(\d+|ten|five|three)\s*[- ]\s*(?:fiscal\s+)?(?:year|yr)s?\b", t)
        if m and re.search(r"\b(?:ago|pehle)\b", t[m.end():]):
            m = None
        # P0.2: "posted over 5 years", "more than 5 years", "for 5 years" describe tenure, not a reporting window
        if m and re.search(r"\b(?:over|more\s+than|for|at\s+least|upto|up\s+to)\s*$|>\s*$", t[:m.start()]):
            m = None
    if m:
        tok = m.group(1)
        n = int(tok) if tok.isdigit() else _WORD_NUM.get(tok)
        if n and 2 <= n <= 15:
            return {"from": fy_label(last - n + 1), "to": fy_label(last), "n_years": n}

    if re.search(r"\b(?:10|ten)\s+(?:years\s+ago|saal\s+pehle)\b", t):
        return {"fy": fy_label(last - 10 + 1)} # FY17

    # Bare 4-digit calendar/fiscal year ("Profit and loss statement of ONGC. 2026", "in 2025")
    m = re.search(r"(?<![-\d])\b(201[7-9]|202[0-7])\b(?![-\d])", t)
    if m:
        return {"fy": fy_label(int(m.group(1)))}

    if re.search(r"\byear before last\b|\bpichle se pichle saal\b", t):
        return {"fy": fy_label(last - 2)}
    if re.search(r"\b(last|previous|prior)\s+(fiscal\s+|financial\s+)?year\b|\blast fy\b|\bpichle saal\b|\bpichhle saal\b|\bpichla saal\b|\bगत वर्ष\b|\bपिछले साल\b", t):
        return {"fy": fy_label(last - 1)}
    if re.search(r"\b(next|coming)\s+(fiscal\s+|financial\s+)?year\b|\bagle saal\b", t):
        return {"fy": fy_label(cur + 1)}
    if re.search(r"\b(this|current|present)\s+(fiscal\s+|financial\s+)?year\b|\bthis fy\b|\bcurrent fy\b|\bis saal\b|\bयह साल\b|\bइस साल\b|\bytd\b|\byear[- ]to[- ]date\b", t):
        cur_lbl = fy_label(cur)
        if not avail or cur_lbl in avail:
            return {"fy": cur_lbl, "ytd": True}
        older = [a for a in avail if a <= cur_lbl]
        return {"fy": older[-1] if older else fy_label(last)}
    return None


# ------------------------------------------------------------------ categorical
@lru_cache(maxsize=1)
def load_catalog() -> Dict[str, Any]:
    if not CATALOG_PATH.exists():
        logger.warning("semantic_catalog.json not found; categorical normalisation disabled")
        return {"tables": {}}
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


# Accepts hrfin_x.t, `hrfin_x.t`, proj.hrfin_x.t, `proj.hrfin_x.t` and `proj`.hrfin_x.t (the form
# produced by SemanticLayer.apply_query_craft_rules' project qualification).
_TABLE_RE = re.compile(r"(?:FROM|JOIN)\s+`?(?:[\w-]+`?\.`?)?(hrfin_\w+)`?\.`?(\w+)`?", re.IGNORECASE)
# Unqualified table names resolve against query_data's default dataset (hrfin_silver).
_BARE_TABLE_RE = re.compile(r"(?:FROM|JOIN)\s+`?([A-Za-z_]\w*)`?(?=[\s),;]|$)", re.IGNORECASE)
DEFAULT_DATASET = "hrfin_silver"
_EQ_RE = re.compile(
    r"(?P<lower>LOWER\s*\(\s*)?(?P<col>(?:\b\w+\.)?\b(?P<name>[A-Za-z_]\w*))(?P<close>\s*\))?\s*"
    r"(?P<op>=|!=|<>)\s*'(?P<val>[^']*)'",
    re.IGNORECASE,
)
_IN_RE = re.compile(
    r"(?P<lower>LOWER\s*\(\s*)?(?P<col>(?:\b\w+\.)?\b(?P<name>[A-Za-z_]\w*))(?P<close>\s*\))?\s+"
    r"(?P<not>NOT\s+)?IN\s*\((?P<vals>\s*'[^']*'(?:\s*,\s*'[^']*')*\s*)\)",
    re.IGNORECASE,
)


def referenced_tables(sql: str) -> List[str]:
    out = [f"{d}.{t}" for d, t in _TABLE_RE.findall(sql or "")]
    known = load_catalog().get("tables", {})
    for name in _BARE_TABLE_RE.findall(sql or ""):
        cand = f"{DEFAULT_DATASET}.{name}"
        if cand in known and cand not in out:
            out.append(cand)
    return out


def categorical_values(tables: Iterable[str], catalog: Optional[Dict[str, Any]] = None) -> Dict[str, Set[str]]:
    """column name -> union of profiled values across the given tables."""
    cat = catalog if catalog is not None else load_catalog()
    out: Dict[str, Set[str]] = {}
    for t in tables:
        cols = (cat.get("tables", {}).get(t) or {}).get("columns", {})
        for name, meta in cols.items():
            if meta.get("values") and str(meta.get("type", "STRING")).upper() == "STRING":
                out.setdefault(name.lower(), set()).update(str(v) for v in meta["values"])
    return out


def _canonical(val: str, values: Set[str]) -> Optional[List[str]]:
    """Stored spellings matching `val` case-insensitively (None when val is not a known value).

    More than one hit means the referenced tables disagree on the spelling, so the
    caller must compare with LOWER() instead of picking one.
    """
    hits = sorted(v for v in values if v.lower() == val.lower())
    return hits or None


def normalize_categorical_filters(sql: str, catalog: Optional[Dict[str, Any]] = None) -> str:
    """Rewrites equality / IN filters on profiled categorical columns to the stored spelling."""
    if not sql:
        return sql
    colvals = categorical_values(referenced_tables(sql), catalog)
    if not colvals:
        return sql

    def eq_sub(m: re.Match) -> str:
        name = m.group("name").lower()
        if name not in colvals or bool(m.group("lower")) != bool(m.group("close")):
            return m.group(0)
        val = m.group("val")
        if m.group("lower"):
            # LOWER(col) = 'X' must compare with a lower-case literal.
            return m.group(0) if val == val.lower() else m.group(0)[: m.start("val") - m.start()] + val.lower() + "'"
        hits = _canonical(val, colvals[name])
        if not hits or hits == [val]:
            return m.group(0)
        if len(hits) == 1:
            return f"{m.group('col')} {m.group('op')} '{hits[0]}'"
        return f"LOWER({m.group('col')}) {m.group('op')} '{val.lower()}'"

    def in_sub(m: re.Match) -> str:
        name = m.group("name").lower()
        if name not in colvals or bool(m.group("lower")) != bool(m.group("close")):
            return m.group(0)  # e.g. UPPER(cadre) IN (...): not ours to rewrite
        if m.group("lower"):
            # LOWER(col) IN ('Mixed') must compare with lower-case literals.
            vals = re.findall(r"'([^']*)'", m.group("vals"))
            if all(v == v.lower() for v in vals):
                return m.group(0)
            neg = "NOT " if m.group("not") else ""
            return f"LOWER({m.group('col')}) {neg}IN (" + ", ".join(f"'{v.lower()}'" for v in vals) + ")"
        vals = re.findall(r"'([^']*)'", m.group("vals"))
        new_vals: List[str] = []
        need_lower = False
        for v in vals:
            hits = _canonical(v, colvals[name])
            if hits and len(hits) > 1:
                need_lower = True
            new_vals.append(hits[0] if hits and len(hits) == 1 else v)
        neg = "NOT " if m.group("not") else ""
        if need_lower:
            return f"LOWER({m.group('col')}) {neg}IN (" + ", ".join(f"'{v.lower()}'" for v in vals) + ")"
        if new_vals == vals:
            return m.group(0)
        return f"{m.group('col')} {neg}IN (" + ", ".join(f"'{v}'" for v in new_vals) + ")"

    out = _IN_RE.sub(in_sub, sql)
    out = _EQ_RE.sub(eq_sub, out)
    if out != sql:
        logger.info("Categorical filters normalised against semantic_catalog.json")
    return out


def fiscal_years_for_sql(sql: str, catalog: Optional[Dict[str, Any]] = None) -> List[str]:
    """FY labels present (per the catalog) in the tables a SQL statement reads."""
    cat = catalog if catalog is not None else load_catalog()
    out: Set[str] = set()
    for t in referenced_tables(sql):
        meta = ((cat.get("tables", {}).get(t) or {}).get("columns", {}) or {}).get("fiscal_year") or {}
        out.update(str(v).upper() for v in meta.get("values") or [] if re.match(r"^FY\d{2}$", str(v).upper()))
    return sorted(out)
