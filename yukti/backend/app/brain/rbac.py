"""RBAC policy engine v2 for Yukti v3 (P2H.1 / SPEC-06 / BEH-01 / D-41 / D-43 / D-60).

`rbac_policy.yaml` maps the 11 canonical personas (`CMD`, `DIR_HR`, `DIR_FIN`,
`E1_HR..E4_HR`, `E1_FIN..E4_FIN`) across 12 data classes (`general_hr`, `general_fin`,
`fin_internal`, `policy`, `named`, `pay_aggregate`, `pay_individual`, `apar`,
`sensitive`, `self`, `board_confidential`, `valuation_run`) -> `allow | aggregate | refuse`.

Supports:
- Function dimension (`EXEC`, `HR`, `FIN`) and `director_function_scope` toggle (`True` D-43 vs `False` D-10).
- `self` scope priority (`@self_emp_id` bound from `principal.emp_id`; compiler-enforced predicate only; zero cross-employee leakage).
- Junior aggregate pay (`pay_aggregate`, k >= 5) from compiled aggregate spec only (closes BUG-07, M3, M4).
- Director post-query enforcement (`enforce_contract` applies D-43 to `DIR_FIN` and `DIR_HR` as well as `E1–E4`).
- Role escalation refusal (`R-ROLE`) for all 10 non-CMD personas.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import yaml

from app.access_control import (
    JUNIOR_FIN_PERSONAS,
    JUNIOR_HR_PERSONAS,
    VALID_PERSONAS,
    UnknownPersona,
    normalize_persona,
)
from app.auth import PERSONA_DIRECTORY, is_role_switch_request
from app.brain.query_spec import QuerySpec

POLICY_PATH = Path(__file__).resolve().parent / "rbac_policy.yaml"
_ORDER = {"allow": 0, "mask": 1, "aggregate": 2, "refuse": 3}
_COUNT_COL = re.compile(r"(headcount|employees|executives|officers|count|num_|staff|people|personnel)", re.I)

V2_DATA_CLASSES: tuple[str, ...] = (
    "general_hr",
    "general_fin",
    "fin_internal",
    "policy",
    "named",
    "pay_aggregate",
    "pay_individual",
    "apar",
    "sensitive",
    "self",
    "board_confidential",
    "valuation_run",
)


@lru_cache(maxsize=1)
def load_policy() -> Dict[str, Any]:
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))


def _canon_or_raw(persona: str) -> Optional[str]:
    try:
        return normalize_persona(persona)
    except UnknownPersona:
        return None


def persona_class(persona: str) -> str:
    """Return `'leadership'`, `'director'`, or `'junior'` (unknown personas -> `'junior'`)."""
    canon = _canon_or_raw(persona) or persona
    for cls, members in (load_policy().get("persona_classes") or {}).items():
        if canon in members:
            return cls
    return "junior"


def persona_role_key(persona: str) -> str:
    """Return the 5-bucket v2 role key (`cmd`, `director_hr`, `director_fin`, `junior_hr`, `junior_fin`)."""
    canon = _canon_or_raw(persona)
    if canon == "CMD":
        return "cmd"
    if canon == "DIR_HR":
        return "director_hr"
    if canon == "DIR_FIN":
        return "director_fin"
    if canon in JUNIOR_HR_PERSONAS:
        return "junior_hr"
    if canon in JUNIOR_FIN_PERSONAS:
        return "junior_fin"
    return "junior_hr"


def persona_function(persona: str) -> str:
    """Return the persona's functional domain (`EXEC`, `HR`, or `FIN`)."""
    canon = _canon_or_raw(persona)
    if canon == "CMD":
        return "EXEC"
    if canon in ("DIR_FIN",) or canon in JUNIOR_FIN_PERSONAS:
        return "FIN"
    return "HR"


@dataclass
class PolicyDecision:
    action: str
    persona_class: str
    data_classes: List[str] = field(default_factory=list)
    trigger: Optional[str] = None           # data class that decided the action
    rule_ref: Optional[str] = None
    reason: Optional[str] = None
    code: Optional[str] = None              # R-NAMED | R-PAY | R-APAR | R-SENS | R-FUNC | R-BOARD | R-ROLE | R-K5
    persona: str = ""
    function: str = ""
    target_function: Optional[str] = None
    self_emp_id: Optional[str] = None


_POLICY_PROCESS_RE = re.compile(
    r"(?:"
    r"\b(?:posh\s+policy|reporting\s+process|complaint\s+(?:process|procedure)|"
    r"policy\s+and\s+(?:the\s+)?reporting\s+process|whistle\s*blower\s+policy|"
    r"what\s+is\s+the\s+(?:posh|vigilance|medical|transfer|leave)\s+policy)\b"
    r"|(?:posh\s*नीति|नीति\s*और\s*(?:शिकायत|रिपोर्टिंग)\s*प्रक्रिया|शिकायत\s*प्रक्रिया\s*क्या\s*है)"
    r")",
    re.IGNORECASE,
)

_SENSITIVE_CASE_OR_RECORD_RE = re.compile(
    r"(?:"
    r"\b(?:cases?|complaints?\s+(?:filed|registered|pending|against|in\s+fy|count|number|list)|"
    r"how\s+many|who\s+is|under\s+vigilance|inquiry\s+against|dossier|records?|claims?\s+of|pending)\b"
    r"|(?:मामले|शिकायतें|कितने|रिकॉर्ड|लंबित)"
    r")",
    re.IGNORECASE,
)


def is_policy_process_question(question: Optional[str]) -> bool:
    """Return True when `question` asks about a policy or reporting process (e.g. POSH policy)
    rather than case records, complaint counts, or individual dossiers (P2H.2 M5 / SPEC-06 §4.6).
    """
    if not question:
        return False
    q = question.strip()
    if not _POLICY_PROCESS_RE.search(q):
        return False
    if _SENSITIVE_CASE_OR_RECORD_RE.search(q):
        return False
    if _EMP_ID_LITERAL_RE.search(q):
        return False
    return True


def topic_classes(question: str) -> List[str]:
    """Sensitive topics in the question (word-boundary match; 'apar' never matches 'apart')."""
    q = (question or "").lower()
    out = []
    for cls, words in (load_policy().get("topic_keywords") or {}).items():
        if any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", q) for w in words):
            out.append(cls)
    return out


_EMP_ID_LITERAL_RE = re.compile(r"\b(EMP-\d{4,6})\b", re.IGNORECASE)

_V2_AGG_PAY_RE = re.compile(
    r"(?:"
    r"\b("
    r"average\s+ctc|avg\.?\s+ctc|mean\s+ctc|median\s+ctc|"
    r"average\s+(?:monthly\s+)?(?:basic\s+)?(?:salary|pay|ctc)\s+(?:of|for)\s+e[1-9](?:\s+(?:officers|executives|staff|employees))?\b|"
    r"average\s+(?:monthly\s+)?(?:basic\s+)?(?:salary|pay|ctc)\s+(?:by\s+grade|across\s+grades|for\s+e[1-9]\s+(?:executives|officers))|"
    r"starting\s+(?:basic\s+)?(?:pay|salary|scale)|"
    r"entry[\s\-]+(?:level\s+)?(?:basic\s+)?(?:pay|salary|scale)|"
    r"minimum\s+(?:basic\s+)?(?:pay|scale)|"
    r"get\s+on\s+joining|joining\s+(?:basic\s+)?(?:pay|salary|scale)|"
    r"pay\s+(?:scale|band|range|matrix|slab)s?|"
    r"grade[\s\-]*wise\s+(?:average\s+|avg\s+)?(?:ctc|salary|pay)"
    r")\b"
    r"|(?:e[1-9]\s*(?:अधिकारियों|कर्मचारियों)?\s*का\s*औसत\s*(?:मासिक\s*)?(?:मूल\s*)?(?:वेतन|सैलरी)|"
    r"औसत\s*(?:मासिक\s*)?(?:मूल\s*)?(?:वेतन|सैलरी))"
    r")",
    re.IGNORECASE,
)

# Non-person capitalized phrases so we don't mistake ONGC entities for a person's name
_NON_PERSON_PROPER_WORDS = {
    "delhi", "mumbai", "dehradun", "ahmedabad", "mehsana", "assam", "tripura", "rajahmundry",
    "chennai", "kolkata", "uran", "hazira", "ankleshwar", "cambay", "bokaro", "jorhat",
    "nazira", "sivasagar", "silchar", "agartala", "kakinada", "karaikal", "vadodara",
    "ongc", "india", "high", "office", "hq", "asset", "basin", "work", "centre", "center",
    "executive", "executives", "officer", "officers", "director", "chairman", "managing",
    "human", "resources", "finance", "accounts", "board", "note", "transfer", "policy",
    "annual", "report", "balance", "sheet", "income", "statement", "cash", "flow",
    "profit", "loss", "schedule", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "january", "february",
}


def _known_persona_identities() -> List[Tuple[str, str, str, str]]:
    """Return `[(persona_id, emp_id_lower, display_name_lower, function)]` for all 11 personas."""
    out = []
    for pid, info in PERSONA_DIRECTORY.items():
        if pid == "DEMO_ADMIN":
            continue
        out.append(
            (
                pid,
                str(info.get("emp_id", "")).lower(),
                str(info.get("display_name", "")).lower(),
                str(info.get("function", "HR")).upper(),
            )
        )
    return out


def _mentions_individual_or_row_pay_target(question: str) -> bool:
    """Return True if `question` names a specific person/employee ID or asks for row-level/per-employee pay."""
    if not question:
        return False
    q = question.strip()
    q_low = q.lower()
    if _EMP_ID_LITERAL_RE.search(q):
        return True
    if re.search(r"\b\d{6}\b", q):
        return True
    for _, _, name_low, _ in _known_persona_identities():
        if name_low and len(name_low) > 3 and name_low in q_low:
            return True
    if re.search(
        r"\b(reporting\s+officer|my\s+boss|my\s+manager|my\s+colleague\w*|my\s+team|"
        r"each\s+(?:employee|officer|executive)|every\s+(?:employee|officer|executive)|"
        r"list\s+(?:the\s+)?(?:net\s+pay|gross\s+pay|basic\s+pay|salary|salaries|ctc|pay)|"
        r"(?:net\s+pay|gross\s+pay|basic\s+pay|salary|salaries|ctc|pay\s+band)\s+of\s+all\b)\b"
        r"|(?:रिपोर्टिंग\s*अधिकारी|मेरे\s*(?:अधिकारी|सहकर्मी|बॉस|मैनेजर|प्रबंधक))"
        r"|(?:का|की|ka|unka|unki|उनका|उनकी|उसका|उसकी)\s*(?:वेतन|तनख्वाह|सैलरी|salary|apar|medical|health)"
        r"|employee\s*id\b.*(?:वेतन|तनख्वाह|सैलरी|salary|apar|medical|health)",
        q_low,
    ):
        return True
    # Check capitalized two-word person name after "of" / "for" or possessive "'s" (e.g. "pay band of Ramesh Kumar")
    for m in re.finditer(r"(?:\b(?:of|for)\s+([A-Z][a-z]{2,})\s+([A-Z][a-z]{2,})\b|\b([A-Z][a-z]{2,})(?:\s+([A-Z][a-z]{2,}))?'s\b)", q):
        words = [w.lower() for w in m.groups() if w]
        if words and not any(w in _NON_PERSON_PROPER_WORDS for w in words):
            return True
    return False


def _detect_self_emp_id(
    canon_persona: Optional[str],
    question: str,
    data_classes: List[str],
    explicit_self_emp_id: Optional[str] = None,
    spec: Optional[QuerySpec] = None,
) -> Optional[str]:
    """Return the caller's `emp_id` ONLY when the compiled query/spec is strictly self-scoped (M3 / SPEC-06 §4.2).

    Never grants `self` from a question-text regex alone.
    """
    if not canon_persona or canon_persona not in PERSONA_DIRECTORY:
        return None
    my_info = PERSONA_DIRECTORY[canon_persona]
    my_emp_id = explicit_self_emp_id or str(my_info.get("emp_id", ""))
    q = (question or "").strip()
    q_low = q.lower()

    # Reject if the question references any other employee ID, known persona name, or non-self group
    mentioned_emp_ids = {m.upper() for m in _EMP_ID_LITERAL_RE.findall(q)}
    if mentioned_emp_ids and mentioned_emp_ids != {my_emp_id.upper()}:
        return None

    for other_pid, _, other_name_low, _ in _known_persona_identities():
        if other_pid == canon_persona:
            continue
        if other_name_low and len(other_name_low) > 3 and other_name_low in q_low:
            return None

    if re.search(
        r"\b(in\s+my\s+opinion|my\s+(?:team|colleague\w*|peer\w*|subordinate\w*|reporting\s+officer|boss|manager)|"
        r"all\s+(?:e[1-9]\s+)?(?:hr\s+|finance\s+)?(?:officer\w*|executive\w*|employee\w*|staff)|"
        r"(?:each|every)\s+(?:officer|executive|employee))\b"
        r"|(?:रिपोर्टिंग\s*अधिकारी|मेरे\s*(?:अधिकारी|सहकर्मी|बॉस|मैनेजर|प्रबंधक|अधीनस्थ)|मेरी\s*टीम|सभी\s*(?:कर्मचारियों|अधिकारियों))",
        q_low,
    ):
        return None

    # Check if `spec` has a foreign emp_id filter
    spec_has_self_predicate = False
    if spec is not None:
        for f in spec.filters or []:
            if f.field == "emp_id":
                vals = f.value if isinstance(f.value, list) else [f.value]
                norm_vals = {str(v).strip().upper() for v in vals if v is not None}
                if f.op == "=" and norm_vals <= {"@SELF_EMP_ID", my_emp_id.upper()}:
                    spec_has_self_predicate = True
                else:
                    return None
        if spec.self_scope:
            spec_has_self_predicate = True

    # Grant `self` ONLY when the compiled classes include `"self"` or the QuerySpec carries the self predicate
    if "self" in (data_classes or []) or spec_has_self_predicate:
        return my_emp_id

    return None


def _infer_target_function(
    question: str,
    classes: List[str],
    explicit_target: Optional[str] = None,
    spec: Optional[QuerySpec] = None,
) -> str:
    """Infer whether the target data/employee belongs to `'HR'`, `'FIN'`, `'CORP'`, or `'MIXED'` (M5 / D-43)."""
    q = (question or "").strip()
    q_low = q.lower()
    q_up = q.upper()

    # 1. Detect mixed HR + Finance questions (e.g. "APAR of E3 HR officers and the finance officer",
    #    "names of all Delhi staff (DISC-FIN)") -> MIXED (never single-function FIN/HR).
    mentions_hr_group = bool(
        "DISC-HR" in q_up
        or re.search(
            r"\b(hr\s+officer\w*|hr\s+executive\w*|e[1-9]\s+hr\b|hr\s+e[1-9]\b|all\s+(?:delhi\s+)?(?:staff|employees|executives|officers))\b",
            q_low,
        )
    )
    mentions_fin_group = bool(
        "DISC-FIN" in q_up
        or re.search(
            r"\b(finance\s+officer\w*|finance\s+executive\w*|accounts\s+officer\w*|e[1-9]\s+finance\b|finance\s+e[1-9]\b)\b",
            q_low,
        )
    )
    for _, emp_low, name_low, fn in _known_persona_identities():
        if (emp_low and emp_low in q_low) or (name_low and len(name_low) > 3 and name_low in q_low):
            if fn == "FIN":
                mentions_fin_group = True
            elif fn == "HR":
                mentions_hr_group = True

    if mentions_hr_group and mentions_fin_group:
        return "MIXED"

    # 2. When a compiled QuerySpec is available, derive target function from the spec's discipline filter (M5).
    if spec is not None:
        disc_filters = [f for f in (spec.filters or []) if f.field in ("discipline", "discipline_id", "function")]
        if disc_filters:
            all_vals: set[str] = set()
            for df in disc_filters:
                if df.op not in ("=", "in"):
                    return "MIXED"
                vs = df.value if isinstance(df.value, list) else [df.value]
                all_vals |= {str(v).strip().upper() for v in vs if v is not None}
            if all_vals == {"DISC-FIN"} or all_vals == {"FIN"}:
                return "FIN"
            if all_vals == {"DISC-HR"} or all_vals == {"HR"}:
                return "HR"
            return "MIXED"
        # No discipline filter on the spec: for HR workforce/personal classes, unscoped queries span all disciplines
        # (so for DIR_FIN, it is not FIN-scoped; for DIR_HR, HR is the domain owner).
        if any(c in ("fin_internal", "general_fin", "valuation_run") for c in classes) or spec.domain == "finance":
            return "FIN"
        return "HR"

    # 3. Explicit target_function (when question is not mixed)
    if explicit_target:
        return explicit_target.strip().upper()

    # 4. Known persona names / IDs (single function)
    if mentions_fin_group and not mentions_hr_group:
        # Ensure it's not a general "all staff" query with a finance keyword tacked on
        if not re.search(r"\b(all|every)\s+(?:delhi\s+|mumbai\s+)?(?:staff|employees|executives)\b", q_low):
            return "FIN"

    if mentions_hr_group and not mentions_fin_group:
        return "HR"

    if any(c in ("fin_internal", "general_fin", "valuation_run") for c in classes):
        return "FIN"
    if "board_confidential" in classes:
        if any(w in q_low for w in ("divestment", "marginal field", "valuation")):
            return "FIN"
        return "HR"
    return "HR"


def _enrich_classes_from_question(
    question: str,
    base_classes: List[str],
    pc: str,
    spec: Optional[QuerySpec] = None,
) -> List[str]:
    """Derive v2 data classes from `question` and `base_classes` without ever dropping compiler classes (M3, M4, S3)."""
    q = (question or "").strip()
    q_low = q.lower()
    # Keep ALL compiler-derived base classes intact (never strip pay_individual, named, apar, sensitive)
    classes = list(base_classes or ["general"])
    if spec is not None and spec.domain == "hr" and not spec.self_scope:
        classes = ["general_hr" if c == "general" else c for c in classes]

    if not q:
        return classes

    if is_policy_process_question(q):
        if "policy" not in classes:
            classes.append("policy")

    # M4: If a specific person or row-grain pay target is mentioned in a pay question, always add pay_individual
    # and remove pay_aggregate so individual/named pay is never misclassified as aggregate pay.
    t_classes = topic_classes(q)
    has_pay_word = "pay" in t_classes or bool(
        re.search(
            r"\b(pay\s+(?:scale|band|range|matrix|slab)s?|starting\s+pay|joining\s+pay|basic\s+pay|net\s+pay|gross\s+pay|salary|ctc)\b|(?:वेतन|सैलरी)",
            q_low,
        )
    )
    if has_pay_word and _mentions_individual_or_row_pay_target(q):
        classes = [c for c in classes if c != "pay_aggregate"]
        if "pay_individual" not in classes and "pay" not in classes:
            classes.append("pay" if "general" in base_classes else "pay_individual")
    elif (
        has_pay_word
        and _V2_AGG_PAY_RE.search(q)
        and not _mentions_individual_or_row_pay_target(q)
        and not any(c in ("pay_individual", "pay", "named") for c in base_classes)
        and (spec is None or (spec.grain == "aggregate" and not any(f.field in ("emp_id", "name") for f in (spec.filters or []))))
    ):
        if "pay_aggregate" not in classes:
            classes.append("pay_aggregate")

    # Board confidential succession / divestment / deliberation notes
    if re.search(r"\b(?:confidential\s+board|board\s+(?:hr\s+)?(?:succession|divestment)\s+note)\b", q_low):
        if "board_confidential" not in classes:
            classes.append("board_confidential")

    # Internal finance ledger / vendor ageing / cost-centre opex
    if re.search(
        r"\b(?:vendor[\s\-]*level\s+age?ing|internal\s+cost[\s\-]*cent(?:re|er)\s+ledger|"
        r"cost[\s\-]*cent(?:re|er)\s+opex)\b",
        q_low,
    ):
        if "fin_internal" not in classes:
            classes.append("fin_internal")

    # S3: Valuation model run (only DCF / valuation model execution, NEVER bare WACC which is general_fin)
    if re.search(
        r"\b(?:dcf\s+valuation|run\s+a?\s*(?:dcf|valuation)|compute\s+a?\s*(?:dcf|valuation)|valuation\s+model\s+run)\b",
        q_low,
    ):
        if "valuation_run" not in classes:
            classes.append("valuation_run")

    # Named roster / overdue cohort email request
    if re.search(
        r"\b(?:list\s+the\s+names|names\s+of\s+(?:executives|delhi\s+staff|finance\s+officers|staff|officers)|"
        r"show\s+the\s+names|who\s+are\s+the\s+executives|overdue\s+cohort)\b",
        q_low,
    ):
        if "named" not in classes:
            classes.append("named")

    # Topic keywords (pay, apar, sensitive)
    if pc in ("junior", "director") or any(tc in ("pay", "apar", "sensitive") for tc in t_classes):
        for tc in t_classes:
            if tc == "pay":
                if "pay" not in classes and "pay_individual" not in classes and "pay_aggregate" not in classes:
                    classes.append("pay" if "general" in base_classes else "pay_individual")
            elif tc not in classes:
                classes.append(tc)

    return classes


def action_for(
    persona: str,
    data_class: str,
    *,
    target_function: Optional[str] = None,
    director_function_scope: Optional[bool] = None,
) -> str:
    """Return `'allow'`, `'aggregate'`, or `'refuse'` for `(persona, data_class)`."""
    act, _ = _resolve_class_action(
        persona,
        data_class,
        target_function=target_function,
        director_function_scope=director_function_scope,
    )
    return act


def _resolve_class_action(
    persona: str,
    data_class: str,
    *,
    target_function: Optional[str] = None,
    director_function_scope: Optional[bool] = None,
) -> Tuple[str, Optional[str]]:
    """Resolve `(action, refusal_or_mask_code)` from `rbac_policy.yaml`."""
    pol = load_policy()
    role_key = persona_role_key(persona)
    p_func = persona_function(persona)
    dir_scope = (
        bool(pol.get("director_function_scope", True))
        if director_function_scope is None
        else bool(director_function_scope)
    )

    # Map legacy v1 data class names to v2 data_classes entries
    dc_norm = data_class
    if dc_norm == "general":
        return "allow", None
    if dc_norm == "pay":
        dc_norm = "pay_individual"

    dc_cfg = (pol.get("data_classes") or {}).get(dc_norm)
    if not isinstance(dc_cfg, dict):
        return "refuse", "R-NAMED"

    # When director_function_scope=False (D-10 mode), Directors have full cross-functional allow
    if not dir_scope and role_key in ("director_hr", "director_fin"):
        return "allow", None

    raw_action = dc_cfg.get(role_key, "refuse")
    default_code = dc_cfg.get("refusal_code")

    allowed_funcs = set((pol.get("functions") or {}).get(p_func, [p_func, "CORP"]))
    eff_target = (target_function or ("FIN" if dc_norm in ("fin_internal", "general_fin", "valuation_run") else "HR")).upper()

    if raw_action == "function_scoped":
        if eff_target in allowed_funcs:
            return "allow", None
        return "aggregate", (default_code or "R-FUNC")

    if raw_action == "function_scoped_refuse":
        if eff_target in allowed_funcs:
            return "allow", None
        return "refuse", (default_code or "R-FUNC")

    if raw_action == "allow":
        return "allow", None
    if raw_action == "aggregate":
        if dc_norm == "fin_internal":
            return "aggregate", "R-FUNC"
        if dc_norm == "sensitive":
            return "aggregate", "R-SENS"
        return "aggregate", (default_code or "R-NAMED")
    return "refuse", (default_code or "R-NAMED")


def refusal_text(persona: str, template_key: str, lang: str = "en") -> str:
    """Format a bilingual refusal message from `rbac_policy.yaml`."""
    pol = load_policy()
    canon = _canon_or_raw(persona) or "E2_HR"
    p_meta = (pol.get("personas") or {}).get(canon, {})
    label = p_meta.get("label") or canon
    fn = p_meta.get("function") or persona_function(canon)
    templates = pol.get("refusal_templates") or {}
    entry = templates.get(template_key) or templates.get("default") or {}
    msg = entry.get("hi" if lang == "hi" else "en") or entry.get("en") or "Access restricted for your current role."
    return msg.format(persona_label=label, persona_function=fn, persona=canon)


def decide(
    persona: str,
    data_classes: Optional[List[str]] = None,
    question: str = "",
    *,
    target_function: Optional[str] = None,
    director_function_scope: Optional[bool] = None,
    self_emp_id: Optional[str] = None,
    spec: Optional[QuerySpec] = None,
) -> PolicyDecision:
    """Evaluate RBAC policy for `(persona, data_classes, question)` and return `PolicyDecision`.

    S4 / SPEC-06 §4.4: `persona` must be one of the 11 canonical personas (`Principal.persona`);
    empty, unknown, or un-normalized aliases raise `UnknownPersona`.
    """
    if not persona or not isinstance(persona, str) or persona.strip().upper() not in VALID_PERSONAS:
        raise UnknownPersona(f"decide() requires a canonical persona in {sorted(VALID_PERSONAS)}, got {persona!r}")
    canon = persona.strip().upper()
    pc = persona_class(canon)
    p_func = persona_function(canon)
    pol = load_policy()
    refs = pol.get("rule_refs", {})

    # 1. Role escalation check (R-ROLE, SPEC-06 §4.4 / Q18)
    in_classes = list(data_classes or [])
    if "role_escalation" in in_classes or (question and is_role_switch_request(question)):
        if canon == "CMD":
            return PolicyDecision(
                action="allow",
                persona_class=pc,
                data_classes=["role_escalation"],
                trigger=None,
                rule_ref=refs.get("D-41"),
                reason=None,
                code=None,
                persona=canon,
                function=p_func,
                target_function="ANY",
            )
        return PolicyDecision(
            action="refuse",
            persona_class=pc,
            data_classes=["role_escalation"],
            trigger="role_escalation",
            rule_ref=refs.get("D-41") or "SPEC-06 §4.4",
            reason=refusal_text(canon, "role_escalation"),
            code="R-ROLE",
            persona=canon,
            function=p_func,
            target_function="ANY",
        )

    # 2. Self-scope check (M3 / SPEC-06 §4.2 & §5.3: granted ONLY when compiled spec/data_classes carry `self`)
    detected_self_id = _detect_self_emp_id(canon, question, in_classes, explicit_self_emp_id=self_emp_id, spec=spec)
    if detected_self_id:
        return PolicyDecision(
            action="allow",
            persona_class=pc,
            data_classes=["self"],
            trigger="self",
            rule_ref="SPEC-06 §5.3",
            reason="Self-service query bound to @self_emp_id.",
            code=None,
            persona=canon,
            function=p_func,
            target_function="SELF",
            self_emp_id=detected_self_id,
        )

    # 3. Enrich classes and target_function from question & compiled spec (M4, M5)
    classes = _enrich_classes_from_question(question, in_classes or ["general"], pc, spec=spec)
    eff_target = _infer_target_function(question, classes, explicit_target=target_function, spec=spec)

    # SPEC-06 §6 Q18: Finance junior drafting an HR cohort/transfer email -> refuse (R-FUNC)
    if (
        pc == "junior"
        and p_func == "FIN"
        and question
        and re.search(r"\bdraft\b.*\b(?:director\s+hr|overdue\s+cohort|transfer\s+note)\b", question, re.I)
    ):
        return PolicyDecision(
            action="refuse",
            persona_class=pc,
            data_classes=sorted(set(classes)),
            trigger="named",
            rule_ref=refs.get("D-43") or refs.get("D-11"),
            reason=refusal_text(canon, "function_mismatch"),
            code="R-FUNC",
            persona=canon,
            function=p_func,
            target_function="HR",
        )

    worst = "allow"
    trigger: Optional[str] = None
    worst_code: Optional[str] = None

    for c in sorted(set(classes)):
        call_target = eff_target
        if not question and target_function is None and spec is None and c == "pay":
            call_target = p_func
        act, code = _resolve_class_action(
            canon,
            c,
            target_function=call_target,
            director_function_scope=director_function_scope,
        )
        if _ORDER[act] > _ORDER[worst]:
            worst, trigger, worst_code = act, c, code

    ref = refs.get("D-11") if pc == "junior" and worst != "allow" else (refs.get("D-43") or refs.get("D-10") if pc != "junior" else None)
    reason = None
    if worst == "aggregate":
        if pc == "junior":
            reason = "Individual names and postings are restricted for E1–E4 officers; showing aggregate counts instead."
        else:
            reason = f"Cross-functional detail is aggregated for {canon} under D-43."
    elif worst == "refuse":
        if worst_code == "R-FUNC":
            reason = refusal_text(canon, "function_mismatch")
        elif worst_code == "R-BOARD":
            reason = refusal_text(canon, "board_confidential")
        else:
            reason = (
                {
                    "pay": "Pay and compensation records",
                    "pay_individual": "Pay and compensation records",
                    "apar": "APAR ratings and scores",
                    "sensitive": "Vigilance, POSH and medical records",
                    "board_confidential": "Board-confidential succession notes",
                }.get(trigger or "", "These records")
                + (" are confidential for E1–E4 officers." if pc == "junior" else f" outside your functional scope are restricted under D-43 ({canon}).")
            )

    return PolicyDecision(
        action=worst,
        persona_class=pc,
        data_classes=sorted(set(classes)),
        trigger=trigger,
        rule_ref=ref,
        reason=reason,
        code=worst_code,
        persona=canon,
        function=p_func,
        target_function=eff_target,
    )


def to_aggregate(spec: QuerySpec) -> QuerySpec:
    """Roster -> counts (by grade unless the spec already has a breakdown)."""
    data = spec.model_dump(by_alias=True)
    data["grain"] = "aggregate"
    if not data.get("dimensions"):
        data["dimensions"] = [load_policy().get("aggregate_dimension_default", "grade")]
    sort_obj = data.get("sort")
    if isinstance(sort_obj, dict) and sort_obj.get("by") not in (data.get("dimensions") or []):
        data["sort"] = None
    return QuerySpec.model_validate(data)


def suppress_small_cells(
    rows: List[Dict[str, Any]],
    value_columns: List[str],
    threshold: Optional[int] = None,
    by_name: bool = True,
    cell_count_col: Optional[str] = None,
    value_check: bool = True,
) -> Tuple[List[Dict[str, Any]], int]:
    """Counts below the threshold become '<5' (D-11 / R-K5). Applies secondary suppression if exactly 1 cell is suppressed."""
    t = threshold or int(load_policy().get("small_cell_threshold", 5))
    out = [dict(r) for r in rows]
    n = 0
    for i, r2 in enumerate(out):
        small_cell = (
            cell_count_col is not None
            and isinstance(r2.get(cell_count_col), (int, float))
            and 0 < r2[cell_count_col] < t
        )
        for c in value_columns:
            v = r2.get(c)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            if small_cell or (value_check and 0 < v < t and (not by_name or _COUNT_COL.search(c))):
                out[i][c] = f"<{t}"
                n += 1

    for c in value_columns:
        num_suppressed = sum(1 for r in out if r.get(c) == f"<{t}")
        if num_suppressed == 1:
            min_val = None
            min_idx = -1
            for i, r in enumerate(out):
                v = r.get(c)
                if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
                    if min_val is None or v < min_val:
                        min_val = v
                        min_idx = i
            if min_idx != -1:
                out[min_idx][c] = f"<{t}"
                n += 1

    for r2 in out:
        if cell_count_col:
            r2.pop(cell_count_col, None)
    return out, n


def column_class(col: str) -> Optional[str]:
    """Exact column list first, then patterns (legacy SQL aliases like avg_salary, gross_pay, apar)."""
    pol = load_policy()
    for cls, cols in (pol.get("column_classes") or {}).items():
        if col in cols:
            return cls
    for cls, pats in (pol.get("column_patterns") or {}).items():
        if any(re.search(p, col or "", re.I) for p in pats):
            return cls
    return None


def row_actions(persona: str, subject: Optional[str]) -> List[Dict[str, Any]]:
    pc = persona_class(persona)
    if pc == "junior":
        return []
    out = []
    raw_actions = load_policy().get("row_actions") or []
    if isinstance(raw_actions, list):
        for ra in raw_actions:
            if subject in (ra.get("subjects") or []):
                out.append({k: ra[k] for k in ("id", "label", "action", "question_template") if k in ra})
    elif isinstance(raw_actions, dict) and subject in raw_actions:
        for ra in raw_actions.get(subject) or []:
            out.append({k: ra[k] for k in ("id", "label", "action", "question_template") if k in ra})
    return out


def _strip_columns(table: Dict[str, Any], masked: List[str]) -> None:
    cols = table.get("columns") or []
    table["columns"] = [c for c in cols if c not in masked]
    rows = table.get("rows") or []
    new_rows = []
    for r in rows:
        if isinstance(r, dict):
            new_rows.append({k: v for k, v in r.items() if k not in masked})
        elif isinstance(r, list) and cols:
            new_rows.append([v for c, v in zip(cols, r) if c not in masked])
        else:
            new_rows.append(r)
    table["rows"] = new_rows


def _row_discipline_is_fin(row: Dict[str, Any]) -> Optional[bool]:
    """Return True if row is explicitly Finance, False if explicitly non-Finance, None if row has no discipline column."""
    for k in ("discipline_id", "discipline", "function", "discipline_name"):
        if k in row and row[k] is not None:
            val = str(row[k]).strip().upper()
            if val in ("DISC-FIN", "FIN", "FINANCE", "FINANCE & ACCOUNTS"):
                return True
            return False
    return None


def _verified_self_bypass(c: Dict[str, Any], canon_persona: Optional[str]) -> bool:
    """M3: Return True ONLY when every returned row belongs to the signed principal (`emp_id == self_id`)
    or when the compiler signed `self_scope=True` with `emp_id = @self_emp_id` and no foreign `emp_id` exists.
    A missing `emp_id` column on an untrusted table never passes as self-scoped.
    """
    if not canon_persona or canon_persona not in PERSONA_DIRECTORY:
        return False
    expected_self = str(PERSONA_DIRECTORY[canon_persona].get("emp_id", "")).upper()
    access = c.get("access") or {}
    self_id = str(access.get("self_emp_id") or "").strip().upper()
    if not self_id or self_id != expected_self or access.get("status") != "allowed":
        return False

    vis = c.get("visual") or {}
    tbl = vis.get("table")
    rows = (tbl.get("rows") or []) if isinstance(tbl, dict) else []
    compiler_signed = (
        bool((c.get("query_spec") or {}).get("self_scope"))
        and "emp_id = @self_emp_id" in str(c.get("generated_sql") or "")
    )
    if rows:
        all_have_emp_id = all(isinstance(r, dict) and bool(r.get("emp_id")) for r in rows)
        any_foreign = any(
            isinstance(r, dict) and r.get("emp_id") and str(r.get("emp_id")).strip().upper() != expected_self
            for r in rows
        )
        if any_foreign:
            return False
        if all_have_emp_id or compiler_signed:
            return True
        return False
    return compiler_signed


def _scrub_leaked_values_from_contract(c: Dict[str, Any], vis: Dict[str, Any], masked_values: List[str], rule_label: str = "D-11") -> None:
    texts = (
        [c.get("spoken_summary") or "", c.get("display_text") or "", c.get("caveat") or ""]
        + [str(i) for i in c.get("insights") or []]
        + [str((vis.get("document") or {}).get("markdown") or "")]
    )
    leaked = any(v and v in t for v in set(masked_values) for t in texts)
    if leaked or vis.get("type") == "document":
        safe = (
            f"This answer contains personal details that are restricted for your role ({rule_label}), "
            "so only the permitted summary is shown."
        )
        c["spoken_summary"] = safe
        c["display_text"] = safe
        c["insights"] = [safe]
        c.pop("insights_v2", None)
        c.pop("caveat", None)
        if vis.get("type") == "document":
            vis["type"] = "table" if vis.get("table") else "none"
            vis.pop("document", None)


def enforce_contract(
    contract: Dict[str, Any],
    persona: str,
    *,
    director_function_scope: Optional[bool] = None,
) -> Dict[str, Any]:
    """Post-query guard on any contract (planner or legacy). Idempotent.

    Applies to both `junior` (D-11) and `director` when `director_function_scope=True` (D-43 / M5).
    """
    c = contract
    canon = _canon_or_raw(persona)
    pc = persona_class(canon or persona)
    vis = c.get("visual") or {}
    access = c.setdefault("access", {"status": "allowed"})

    # Consistency rule: a refusal never ships a granular visual.
    if access.get("status") == "refused":
        if vis.get("type") not in ("refusal", "none", None):
            vis["type"] = "refusal"
        vis.pop("chart", None)
        vis.pop("compare", None)
        vis.pop("document", None)
        tbl = vis.get("table")
        if isinstance(tbl, dict):
            granular = [col for col in (tbl.get("columns") or []) if column_class(col)]
            if granular:
                _strip_columns(tbl, granular)
            tbl.setdefault(
                "masking",
                {
                    "level": "refused",
                    "reason": access.get("reason") or "Restricted",
                    "rule_ref": access.get("rule_ref") or "D-11",
                },
            )
        return c

    if pc == "leadership":
        return c

    # Verified self-scope bypass (M3): every row must have emp_id == principal.emp_id (or compiler-signed @self_emp_id)
    if _verified_self_bypass(c, canon):
        return c

    pol = load_policy()
    threshold = int(pol.get("small_cell_threshold", 5))
    dir_scope = (
        bool(pol.get("director_function_scope", True))
        if director_function_scope is None
        else bool(director_function_scope)
    )

    # ── Director post-query enforcement under D-43 (M5) ──────────────────────────
    if pc == "director":
        if not dir_scope:
            return c
        masked_all: List[str] = []
        masked_values: List[str] = []
        suppressed = 0

        if canon == "DIR_FIN":
            # 1. Sensitive columns (POSH / vigilance / medical) are always aggregated (k >= 5) for DIR_FIN
            # 2. Named / pay / APAR rows: keep Finance rows if rows carry discipline; otherwise strip restricted columns
            #    unless the query was explicitly scoped to FIN (`target_function == "FIN"` or `DISC-FIN` in SQL).
            sql_str = str(c.get("generated_sql") or "").upper()
            is_fin_scoped_query = (
                str(access.get("target_function") or "").upper() == "FIN"
                or ("DISC-FIN" in sql_str and "DISC-HR" not in sql_str)
            )
            filtered_non_fin_rows = False
            had_apar = False
            had_pay = False
            had_sens = False

            for tbl in [vis.get("table")] + [it for it in ((vis.get("compare") or {}).get("items") or [])]:
                if not isinstance(tbl, dict) or "columns" not in tbl:
                    continue
                cols = tbl.get("columns") or []
                sens_cols = [col for col in cols if column_class(col) == "sensitive"]
                if sens_cols:
                    had_sens = True
                    for r in tbl.get("rows") or []:
                        if isinstance(r, dict):
                            masked_values += [str(r[m]) for m in sens_cols if r.get(m) is not None and len(str(r[m])) > 2]
                    _strip_columns(tbl, sens_cols)
                    masked_all += sens_cols

                hr_personal_cols = [col for col in (tbl.get("columns") or []) if column_class(col) in ("named", "pay", "apar")]
                if hr_personal_cols:
                    if any(column_class(col) == "apar" for col in hr_personal_cols):
                        had_apar = True
                    if any(column_class(col) == "pay" for col in hr_personal_cols):
                        had_pay = True
                    rows = tbl.get("rows") or []
                    row_flags = [_row_discipline_is_fin(r) for r in rows if isinstance(r, dict)]
                    if rows and any(f is not None for f in row_flags):
                        fin_rows = [r for r in rows if isinstance(r, dict) and (_row_discipline_is_fin(r) is True or r.get("emp_id") is None)]
                        non_fin_rows = [r for r in rows if isinstance(r, dict) and _row_discipline_is_fin(r) is not True and r.get("emp_id") is not None]
                        if non_fin_rows:
                            filtered_non_fin_rows = True
                            for r in non_fin_rows:
                                for col in hr_personal_cols:
                                    if isinstance(r.get(col), str) and len(str(r[col])) > 2:
                                        masked_values.append(str(r[col]))
                            tbl["rows"] = fin_rows
                            if "total_rows" in tbl:
                                tbl["total_rows"] = len(fin_rows)
                    elif not is_fin_scoped_query:
                        for r in rows:
                            if isinstance(r, dict):
                                masked_values += [str(r[m]) for m in hr_personal_cols if r.get(m) is not None and len(str(r[m])) > 2]
                        _strip_columns(tbl, hr_personal_cols)
                        masked_all += hr_personal_cols

                if had_sens or masked_all:
                    rows = tbl.get("rows") or []
                    if rows and isinstance(rows[0], dict):
                        tbl["rows"], n_s = suppress_small_cells(rows, list(rows[0].keys()), threshold)
                        suppressed += n_s

            if masked_all or filtered_non_fin_rows or suppressed:
                _scrub_leaked_values_from_contract(c, vis, masked_values, rule_label="D-43")
                code = "R-SENS" if had_sens else ("R-APAR" if had_apar else ("R-PAY" if had_pay else "R-FUNC"))
                access["status"] = "partial"
                access["code"] = code
                access["rule_ref"] = pol.get("rule_refs", {}).get("D-43", "D-43")
                access["reason"] = (
                    "Under D-43 function scope, non-Finance HR personal records are restricted for Director (Finance); showing Finance scope only."
                )
                tbl = vis.get("table")
                if isinstance(tbl, dict):
                    tbl["masking"] = {
                        "level": "partial" if filtered_non_fin_rows else "aggregate",
                        "code": code,
                        "masked_columns": sorted(set(masked_all)),
                        "reason": access["reason"],
                        "rule_ref": "D-43",
                    }
            return c

        if canon == "DIR_HR":
            # DIR_HR sees fin_internal only as aggregates (D-43)
            for tbl in [vis.get("table")] + [it for it in ((vis.get("compare") or {}).get("items") or [])]:
                if not isinstance(tbl, dict) or "columns" not in tbl:
                    continue
                fin_cols = [col for col in (tbl.get("columns") or []) if column_class(col) == "fin_internal"]
                if fin_cols:
                    for r in tbl.get("rows") or []:
                        if isinstance(r, dict):
                            masked_values += [str(r[m]) for m in fin_cols if r.get(m) is not None and len(str(r[m])) > 2]
                    _strip_columns(tbl, fin_cols)
                    masked_all += fin_cols
            if masked_all:
                _scrub_leaked_values_from_contract(c, vis, masked_values, rule_label="D-43")
                access["status"] = "partial"
                access["code"] = "R-FUNC"
                access["rule_ref"] = pol.get("rule_refs", {}).get("D-43", "D-43")
                access["reason"] = "Internal Finance ledger columns are aggregated for Director (HR) under D-43."
                tbl = vis.get("table")
                if isinstance(tbl, dict):
                    tbl["masking"] = {
                        "level": "aggregate",
                        "code": "R-FUNC",
                        "masked_columns": sorted(set(masked_all)),
                        "reason": access["reason"],
                        "rule_ref": "D-43",
                    }
            return c

        return c

    # ── Junior (E1–E4) post-query enforcement under D-11 (M3, M4) ────────────────
    # M4: allow_pay_aggregate is honoured ONLY when the contract is a true aggregate (no named columns in table,
    # query_spec.grain == "aggregate", no emp_id filter, and dimensions within the allowed cohort set).
    qspec = c.get("query_spec") or {}
    tbl_check = vis.get("table") or {}
    has_named_col = any(column_class(col) == "named" for col in (tbl_check.get("columns") or []))
    allow_agg_pay = bool(
        access.get("allow_pay_aggregate")
        and not has_named_col
        and qspec.get("grain", "aggregate") == "aggregate"
        and not any((f.get("field") in ("emp_id", "name", "emp_name")) for f in (qspec.get("filters") or []) if isinstance(f, dict))
    )

    masked_all = []
    masked_values = []
    suppressed = 0
    restricted_classes = ("named", "apar", "sensitive", "fin_internal") if (allow_agg_pay and canon in JUNIOR_HR_PERSONAS) else (
        ("named", "apar", "sensitive") if allow_agg_pay else (
            ("named", "pay", "apar", "sensitive", "fin_internal") if canon in JUNIOR_HR_PERSONAS else ("named", "pay", "apar", "sensitive")
        )
    )

    for tbl in [vis.get("table")] + [it for it in ((vis.get("compare") or {}).get("items") or [])]:
        if not isinstance(tbl, dict) or "columns" not in tbl:
            continue
        masked = [col for col in (tbl.get("columns") or []) if column_class(col) in restricted_classes]
        if masked:
            for r in tbl.get("rows") or []:
                if isinstance(r, dict):
                    masked_values += [str(r[m]) for m in masked if r.get(m) is not None and len(str(r[m])) > 2]
            _strip_columns(tbl, masked)
            masked_all += masked
        if access.get("status") != "refused":
            rows = tbl.get("rows") or []
            if rows and isinstance(rows[0], dict):
                tbl["rows"], n_s = suppress_small_cells(rows, list(rows[0].keys()), threshold)
                suppressed += n_s
    if vis.get("chart") and isinstance(vis["chart"].get("data"), list):
        data = vis["chart"]["data"]
        if data and isinstance(data[0], dict):
            if any(column_class(k) in restricted_classes for k in data[0].keys()):
                vis.pop("chart", None)
                vis["type"] = "table" if vis.get("table") else "none"
            else:
                vis["chart"]["data"], _ = suppress_small_cells(data, list(data[0].keys()), threshold)
    # Personal values must not survive in any text field or document (G4 B3 B-3).
    if masked_all:
        _scrub_leaked_values_from_contract(c, vis, masked_values, rule_label="D-11")
    if suppressed and access.get("status") == "allowed" and not masked_all:
        access["status"] = "partial"
        access["reason"] = f"{suppressed} cell(s) below {threshold} shown as <{threshold} for E1–E4 officers"
        access["rule_ref"] = pol.get("rule_refs", {}).get("D-11")
        access["code"] = "R-K5"
        tbl = vis.get("table")
        if isinstance(tbl, dict):
            tbl.setdefault("masking", {"level": "aggregate", "reason": access["reason"], "rule_ref": "D-11", "code": "R-K5"})
    
    # Defence in depth: refuse outright if pay/apar/sensitive found for junior
    if any(column_class(c) in ("pay", "apar", "sensitive") for c in masked_all) and pc == "junior":
        access["status"] = "refused"
        access["code"] = "R-PAY" if any(column_class(c) == "pay" for c in masked_all) else "R-SENS"
        access["reason"] = refusal_text(canon, "pay_individual" if access["code"] == "R-PAY" else "sensitive")
        # Ensure refusal format
        vis["type"] = "refusal"
        vis.pop("chart", None)
        vis.pop("compare", None)
        vis.pop("document", None)
        if isinstance(vis.get("table"), dict):
            vis["table"]["masking"] = {"level": "refused", "code": access["code"], "reason": access["reason"], "rule_ref": "D-11"}
        c["spoken_summary"] = access["reason"]
        c["display_text"] = access["reason"]
        return c

    if masked_all and access.get("status") == "allowed":
        refs = pol.get("rule_refs", {})
        access["status"] = "partial"
        access["reason"] = "Personal columns hidden for E1–E4 officers: " + ", ".join(sorted(set(masked_all)))
        access["rule_ref"] = refs.get("D-11")
        tbl = vis.get("table")
        if isinstance(tbl, dict):
            tbl["masking"] = {
                "level": "partial",
                "masked_columns": sorted(set(masked_all)),
                "reason": access["reason"],
                "rule_ref": "D-11",
            }
        note = "Some personal details are hidden for your role."
        if note not in (c.get("spoken_summary") or ""):
            c["spoken_summary"] = (c.get("spoken_summary") or "").rstrip() + " " + note
            c["display_text"] = c["spoken_summary"][:590]
    return c
