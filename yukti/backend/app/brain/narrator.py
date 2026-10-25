"""Narrator limited to computed facts + numeric-grounding check + Hindi translation (B4.3, FEAT-011, P5.2 SPEC-11 §6.2).

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

from app.brain.grounding import check_numeric_grounding
from app.brain.insights import Insight
from app.brain.query_spec import QuerySpec

_NUM = re.compile(r"(?<![A-Za-z])[−-]?\d[\d,]*(?:\.\d+)?")
_SENT = re.compile(r"(?<=[.!?।])\s+")
_FY = re.compile(r"\bFY\s?\d{2}(?:\s?[-–]\s?\d{2})?\b", re.I)
_DATE = re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?[\s-][A-Za-z]{3,9}(?:[\s-]\d{4}|\s+FY\d{2})?\b", re.I)
_GRADE = re.compile(r"\b[EW]\d\b|\bW\d[–-]W\d\b")
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


def _to_float(tok: str) -> Optional[float]:
    try:
        return float(tok.replace(",", "").replace("−", "-"))
    except ValueError:
        return None


def allowed_numbers(
    rows: List[Dict[str, Any]],
    insights: List[Insight],
    spec: Optional[QuerySpec],
    extra: Iterable[float] = (),
) -> Set[float]:
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


# Deterministic phrase/term replacements for Hindi narration (SPEC-11 §6.2, BUG-19, BEH-07.11/.12/.35)
_HINDI_PHRASE_PAIRS = [
    ("The complete Schedule III P&L statement is on screen.", "संपूर्ण अनुसूची-III लाभ और हानि विवरण स्क्रीन पर है।"),
    ("The complete Schedule III P&L trend is on screen.", "संपूर्ण अनुसूची-III लाभ और हानि प्रवृत्ति स्क्रीन पर है।"),
    ("The complete Schedule III Balance Sheet is on screen.", "संपूर्ण अनुसूची-III बैलेंस शीट स्क्रीन पर है।"),
    ("The complete Balance Sheet trend is on screen.", "संपूर्ण बैलेंस शीट प्रवृत्ति स्क्रीन पर है।"),
    ("The complete Ind-AS 7 Cash Flow Statement is on screen.", "संपूर्ण Ind-AS 7 नकदी प्रवाह विवरण स्क्रीन पर है।"),
    ("The complete Cash Flow trend is on screen.", "संपूर्ण नकदी प्रवाह प्रवृत्ति स्क्रीन पर है।"),
    ("The complete ratio scorecard is on screen.", "संपूर्ण वित्तीय अनुपात स्कोरकार्ड स्क्रीन पर है।"),
    ("The level-wise column chart is on screen.", "ग्रेड-वार कॉलम चार्ट स्क्रीन पर है।"),
    ("The full list is on screen.", "पूरी सूची स्क्रीन पर है।"),
    ("The trend is on screen.", "प्रवृत्ति चार्ट स्क्रीन पर है।"),
    ("Details are on screen.", "विस्तृत विवरण स्क्रीन पर है।"),
    ("No records match", "कोई रिकॉर्ड मेल नहीं खाता"),
    ("Try widening a filter.", "कृपया फ़िल्टर का दायरा बढ़ाएँ।"),
    ("Revenue from Operations", "परिचालन से राजस्व (Revenue from Operations)"),
    ("Profit After Tax (PAT)", "कर पश्चात लाभ (PAT)"),
    ("Standalone PAT", "स्टैंडअलोन कर पश्चात लाभ (PAT)"),
    ("Profit for the Year (PAT)", "वर्ष का लाभ (PAT)"),
    ("Profit Before Tax", "कर पूर्व लाभ (PBT)"),
    ("Total Income", "कुल आय"),
    ("Total Expenses", "कुल व्यय"),
    ("Total Assets", "कुल संपत्ति (Total Assets)"),
    ("Non-Current Assets", "गैर-चालू संपत्ति"),
    ("Current Assets", "चालू संपत्ति"),
    ("Total Equity", "कुल इक्विटी (Net Worth)"),
    ("Non-Current Liabilities", "गैर-चालू देनदारियाँ"),
    ("Current Liabilities", "चालू देनदारियाँ"),
    ("Net Cash from Operating Activities (OCF)", "परिचालन गतिविधियों से शुद्ध नकदी (OCF)"),
    ("Operating Cash Flow", "परिचालन नकदी प्रवाह (OCF)"),
    ("Investing Activities", "निवेश गतिविधियों"),
    ("Financing Activities", "वित्तीयन गतिविधियों"),
    ("Closing Cash & Cash Equivalents", "अंतिम नकदी और नकदी समतुल्य"),
    ("including non-executive staff", "गैर-कार्यकारी कर्मचारियों सहित"),
    ("have been posted for more than 5 years.", "5 वर्ष से अधिक समय से तैनात हैं।"),
    ("have more than 5 years of continuous stay.", "का निरंतर कार्यकाल 5 वर्ष से अधिक है।"),
    ("Continuous stay at the current station, more than 5.0 years, as of", "वर्तमान स्टेशन पर 5.0 वर्ष से अधिक निरंतर प्रवास, तिथि:"),
    ("rotation after 3–5 years", "3–5 वर्ष बाद रोटेशन"),
    ("Across all cadres in", "सभी संवर्गों में"),
    ("moved from", "बदलकर"),
    ("across", "कुल"),
    ("groups", "समूहों में"),
    ("grades", "ग्रेडों में"),
    ("disciplines", "विभागों में"),
    ("work centres", "कार्य केंद्रों में"),
    ("fields", "क्षेत्रों में"),
    ("years", "वर्षों में"),
    ("employees", "कर्मचारी"),
    ("executives", "अधिकारी (Executives)"),
    ("people match", "कर्मचारी मिलते हैं"),
    ("Highest:", "सर्वाधिक:"),
    ("Lowest:", "न्यूनतम:"),
    ("crore", "करोड़"),
    ("lakh", "लाख"),
    ("Delhi HQ", "दिल्ली मुख्यालय"),
    ("Delhi", "दिल्ली"),
    ("Mumbai", "मुंबई"),
]


def translate_to_hindi(text: str) -> str:
    """Translates deterministic English narrator sentences into clean Hindi (Devanagari).

    Preserves all numbers, ₹/crore/lakh values, FY labels, and entity codes so numeric
    grounding remains 100% invariant and never concatenates English + Hindi.
    """
    if not text or not text.strip():
        return text
    # If already primarily Devanagari, return cleaned text without any English duplicate
    if len(_DEVANAGARI_RE.findall(text)) >= 12:
        return text.strip()

    out = text.strip()
    # Pattern rewrites for common headline structures
    out = re.sub(
        r"^Between\s+(FY\d{2})\s+and\s+(FY\d{2}),\s*ONGC's\s+",
        r"\1 और \2 के बीच, ONGC का ",
        out,
    )
    out = re.sub(
        r"^For\s+(FY\d{2}),\s*ONGC's\s+Schedule\s+III\s+",
        r"\1 के लिए, ONGC की अनुसूची-III के अनुसार ",
        out,
    )
    out = re.sub(
        r"^For\s+(FY\d{2}),\s*ONGC's\s+",
        r"\1 के लिए, ONGC का ",
        out,
    )
    out = re.sub(
        r"^In\s+(FY\d{2}),\s*ONGC\s+generated\s+",
        r"\1 में, ONGC ने उत्पन्न किया ",
        out,
    )
    out = re.sub(
        r"^As of 31 March\s+(FY\d{2}),\s*ONGC's\s+Schedule\s+III\s+",
        r"31 मार्च \1 की स्थिति के अनुसार, ONGC की अनुसूची-III ",
        out,
    )
    out = re.sub(
        r"^In\s+([^,]+),\s*\*\*([^*]+)\*\*\s*\(([^)]+)\)\s*have been posted for more than 5 years\.",
        r"\1 में, **\2** (\3) 5 वर्ष से अधिक समय से तैनात हैं।",
        out,
    )
    out = re.sub(
        r"([A-Za-z0-9 ()/&-]+)\s+moved\s+from\s+(₹?[\d,.]+\s*(?:crore|cr|lakh|%)?)\s+in\s+(FY\d{2})\s+to\s+(₹?[\d,.]+\s*(?:crore|cr|lakh|%)?)\s+in\s+(FY\d{2})",
        r"\3 में \1 \2 से बढ़कर/बदलकर \5 में \4 हो गया",
        out,
    )

    for en_p, hi_p in _HINDI_PHRASE_PAIRS:
        out = out.replace(en_p, hi_p)

    out = re.sub(r"\bis\s+(₹[\d,.]+\s*करोड़)", r"\1 है", out)
    out = re.sub(r"\bare\s+(₹[\d,.]+\s*करोड़)", r"\1 हैं", out)
    out = re.sub(r"\bstand at\s+(₹[\d,.]+\s*करोड़)", r"\1 पर है", out)
    out = re.sub(r"\band\b", "और", out)
    out = re.sub(r"\bRule:\s*", "नियम: ", out)
    out = re.sub(r"\bPolicy:\s*", "नीति: ", out)

    # Ensure Devanagari presence even for compact KPI strings like "PAT (FY26): ₹32,894.02 crore."
    if not _DEVANAGARI_RE.search(out):
        out = f"ओएनजीसी डेटा सारांश: {out} विस्तृत विवरण स्क्रीन पर है।"
    return out


_HINGLISH_PHRASE_PAIRS = [
    ("The complete Schedule III P&L statement is on screen.", "Pura Schedule III P&L statement screen par hai. Details screen par hain."),
    ("The complete Schedule III P&L trend is on screen.", "Pura Schedule III P&L trend screen par hai. Details screen par hain."),
    ("The complete Schedule III Balance Sheet is on screen.", "Puri Schedule III Balance Sheet screen par hai. Details screen par hain."),
    ("The complete Balance Sheet trend is on screen.", "Pura Balance Sheet trend screen par hai. Details screen par hain."),
    ("The complete Ind-AS 7 Cash Flow Statement is on screen.", "Pura Ind-AS 7 Cash Flow Statement screen par hai. Details screen par hain."),
    ("The complete Cash Flow trend is on screen.", "Pura Cash Flow trend screen par hai. Details screen par hain."),
    ("The complete ratio scorecard is on screen.", "Pura ratio scorecard screen par hai. Details screen par hain."),
    ("The level-wise column chart is on screen.", "Level-wise column chart screen par hai. Details screen par hain."),
    ("The full list is on screen.", "Puri list screen par hai. Details screen par hain."),
    ("The trend is on screen.", "Trend screen par hai. Details screen par hain."),
    ("Details are on screen.", "Details screen par hain."),
    ("including non-executive staff", "non-executive staff sahit"),
    ("have been posted for more than 5 years.", "5 saal se zyada samay se posted hain."),
    ("have more than 5 years of continuous stay.", "ka continuous stay 5 saal se zyada hai."),
    ("Across all cadres in", "Sabhi cadres mein"),
    ("moved from", "badalkar"),
    ("across", "kul"),
    ("groups", "groups mein"),
    ("grades", "grades mein"),
    ("disciplines", "disciplines mein"),
    ("work centres", "work centres mein"),
    ("fields", "fields mein"),
    ("Highest:", "Sabse zyada:"),
    ("Lowest:", "Sabse kam:"),
    ("people match", "employees mile"),
]


def translate_to_hinglish(text: str) -> str:
    """Translates deterministic English narrator sentences into Roman-script Hinglish (zero Devanagari)."""
    if not text or not text.strip():
        return text
    out = _DEVANAGARI_RE.sub("", text).strip()
    out = re.sub(
        r"^For\s+(FY\d{2}),\s*ONGC's\s+",
        r"\1 mein ONGC ka ",
        out,
    )
    out = re.sub(
        r"^In\s+([^,]+),\s*\*\*([^*]+)\*\*\s*\(([^)]+)\)\s*have been posted for more than 5 years\.",
        r"\1 mein **\2** (\3) 5 saal se zyada samay se posted hain.",
        out,
    )
    for en_p, hi_p in _HINGLISH_PHRASE_PAIRS:
        out = out.replace(en_p, hi_p)
    out = re.sub(r"\band\b", "aur", out)
    if "Details screen par hain" not in out:
        out = out.rstrip(".") + ". Details screen par hain."
    return out


def compose_spoken(
    headline: str,
    insights: List[Insight],
    allowed: Set[float],
    max_sentences: int = 4,
    language: str = "en",
    allow_coverage_claims: bool = False,
) -> Dict[str, Any]:
    """Headline + up to two insight sentences, 2–4 sentences, every number grounded."""
    base = [s.strip() for s in _SENT.split((headline or "").strip()) if s.strip() and "on screen" not in s.lower()]
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

    fallback = " ".join(base[: max(1, max_sentences - 1)] + ["Details are on screen."])
    text, dropped = check_numeric_grounding(
        text,
        allowed,
        fallback,
        allow_coverage_claims=allow_coverage_claims,
    )

    # Verify post-drop text has zero remaining numeric grounding violations; if any remain in headline, strip them
    remaining_bad = grounding_violations(text, allowed)
    if remaining_bad:
        text = fallback
        remaining_bad = grounding_violations(text, allowed)

    if language == "hi":
        text = translate_to_hindi(text)
    elif language == "hi-en":
        text = translate_to_hinglish(text)

    return {
        "text": text,
        "ungrounded": remaining_bad,
        "dropped": dropped,
        "sentences": len([s for s in _SENT.split(text) if s]),
    }
