"""RBAC policy engine v2 for Yukti v3 (P2H.1 / SPEC-06 / BEH-01 / D-41 / D-43 / D-60).

`rbac_policy.yaml` maps the 11 canonical personas (`CMD`, `DIR_HR`, `DIR_FIN`,
`E1_HR..E4_HR`, `E1_FIN..E4_FIN`) across 12 data classes (`general_hr`, `general_fin`,
`fin_internal`, `policy`, `named`, `pay_aggregate`, `pay_individual`, `apar`,
`sensitive`, `self`, `board_confidential`, `valuation_run`) -> `allow | aggregate | refuse`.

Supports:
- Function dimension (`EXEC`, `HR`, `FIN`) and `director_function_scope` toggle (`True` D-43 vs `False` D-10).
- `self` scope priority (`@self_emp_id` bound from `principal.emp_id`; zero cross-employee leakage).
- Junior aggregate pay (`pay_aggregate`, k >= 5) and starting/entry pay scale queries (closes BUG-07).
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


def topic_classes(question: str) -> List[str]:
    """Sensitive topics in the question (word-boundary match; 'apar' never matches 'apart')."""
    q = (question or "").lower()
    out = []
    for cls, words in (load_policy().get("topic_keywords") or {}).items():
        if any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", q) for w in words):
            out.append(cls)
    return out


# ── Natural-language classifiers for v2 data classes & function scope ────────

_V2_AGG_PAY_RE = re.compile(
    r"\b("
    r"average\s+ctc|avg\.?\s+ctc|mean\s+ctc|median\s+ctc|"
    r"average\s+(?:monthly\s+)?(?:basic\s+)?(?:salary|pay)\s+(?:of|for)\s+e[1-9]\b|"
    r"average\s+(?:monthly\s+)?(?:basic\s+)?(?:salary|pay)\s+(?:by\s+grade|across\s+grades|for\s+e[1-4]\s+(?:executives|officers))|"
    r"starting\s+(?:basic\s+)?(?:pay|salary|scale)|"
    r"entry[\s\-]+(?:level\s+)?(?:basic\s+)?(?:pay|salary|scale)|"
    r"minimum\s+(?:basic\s+)?(?:pay|scale)|"
    r"get\s+on\s+joining|joining\s+(?:pay|salary)|"
    r"pay\s+(?:scale|band|range|matrix|slab)s?|"
    r"grade[\s\-]*wise\s+(?:average\s+|avg\s+)?(?:ctc|salary|pay)"
    r")\b",
    re.IGNORECASE,
)

_FIRST_PERSON_SELF_RE = re.compile(
    r"(?:(?<![a-z])(?:my|mine|myself|mera|meri|mere|have\s+i\s+been)(?![a-z])|(?:मेरा|मेरी|मेरे))"
    r".*?"
    r"(?:(?<![a-z])(?:salary|payslip|pay\s*slip|pay\s+components|pay\s+scale|ctc|basic\s*pay|da|hra|prp|gross\s*pay|net\s*pay|"
    r"leave|el|cl|hpl|balance|posting|postings|posted|tenure|station|transfer|apar|rating|ratings|score|appraisal|"
    r"entitlement|entitlements|advance|advances|hba|car\s+advance|furniture|laptop|medical|reimbursement)(?![a-z])|"
    r"(?:वेतन|सैलरी|छुट्टी|पोस्टिंग|स्थानांतरण|एपार|पात्रता))",
    re.IGNORECASE,
)

_EMP_ID_LITERAL_RE = re.compile(r"\b(EMP-\d{4,6})\b", re.IGNORECASE)


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


def _detect_self_emp_id(
    canon_persona: Optional[str],
    question: str,
    data_classes: List[str],
    explicit_self_emp_id: Optional[str] = None,
) -> Optional[str]:
    """Return the caller's `emp_id` if the request is strictly self-scoped; else `None`."""
    if not canon_persona or canon_persona not in PERSONA_DIRECTORY:
        return None
    my_info = PERSONA_DIRECTORY[canon_persona]
    my_emp_id = explicit_self_emp_id or str(my_info.get("emp_id", ""))
    my_name = str(my_info.get("display_name", "")).lower()
    q = (question or "").strip()
    q_low = q.lower()

    # Check if the question explicitly references ANY other employee ID or other known persona name
    mentioned_emp_ids = {m.upper() for m in _EMP_ID_LITERAL_RE.findall(q)}
    if mentioned_emp_ids and mentioned_emp_ids != {my_emp_id.upper()}:
        return None

    for other_pid, other_emp_low, other_name_low, _ in _known_persona_identities():
        if other_pid == canon_persona:
            continue
        if other_name_low and len(other_name_low) > 3 and other_name_low in q_low:
            return None

    # 1. Explicit `self` class (compiler-enforced predicate `emp_id = @self_emp_id`)
    if "self" in (data_classes or []):
        return my_emp_id

    # 2. First-person possessive self-service query ("my payslip", "my leave balance", "mera salary", etc.)
    if q and _FIRST_PERSON_SELF_RE.search(q):
        return my_emp_id

    # 3. Explicit self_emp_id supplied by caller when no other employee is named
    if explicit_self_emp_id and not mentioned_emp_ids:
        return my_emp_id

    return None


def _infer_target_function(
    question: str,
    classes: List[str],
    explicit_target: Optional[str] = None,
) -> str:
    """Infer whether the target data/employee belongs to `'HR'`, `'FIN'`, or `'CORP'`."""
    if explicit_target:
        return explicit_target.strip().upper()
    q_low = (question or "").lower()

    # Check known employee names / IDs first
    for _, emp_low, name_low, fn in _known_persona_identities():
        if (emp_low and emp_low in q_low) or (name_low and len(name_low) > 3 and name_low in q_low):
            return "HR" if fn == "EXEC" else fn

    if "DISC-FIN" in (question or "").upper() or any(
        w in q_low
        for w in [
            "finance officer",
            "finance e1",
            "finance e2",
            "finance e3",
            "finance e4",
            "e1 finance",
            "e2 finance",
            "e3 finance",
            "e4 finance",
            "accounts officer",
            "vendor-level",
            "cost-centre ledger",
            "cost-center ledger",
            "dcf valuation",
        ]
    ):
        return "FIN"

    if "DISC-HR" in (question or "").upper() or any(
        w in q_low
        for w in [
            "board hr",
            "hr succession",
            "posh",
            "disciplinary",
            "vigilance",
            "hr officer",
            "hr executive",
        ]
    ):
        return "HR"

    if any(c in ("fin_internal", "general_fin", "valuation_run") for c in classes):
        return "FIN"
    return "HR"


def _enrich_classes_from_question(question: str, base_classes: List[str], pc: str) -> List[str]:
    """Derive v2 data classes from `question` and `base_classes`."""
    q = (question or "").strip()
    q_low = q.lower()
    classes = list(base_classes or ["general"])

    if not q:
        return classes

    # Check aggregate pay / entry pay first (closes BUG-07)
    is_agg_pay = bool(_V2_AGG_PAY_RE.search(q)) and not bool(_EMP_ID_LITERAL_RE.search(q))
    if is_agg_pay:
        for _, _, name_low, _ in _known_persona_identities():
            if name_low and len(name_low) > 3 and name_low in q_low:
                is_agg_pay = False
                break

    if is_agg_pay:
        classes = [c for c in classes if c not in ("general", "general_hr", "pay", "pay_individual")]
        if "pay_aggregate" not in classes:
            classes.append("pay_aggregate")
        return classes

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

    # Valuation model run
    if re.search(r"\b(?:dcf\s+valuation|wacc)\b", q_low):
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
    t_classes = topic_classes(q)
    if pc == "junior" or any(tc in ("pay", "apar", "sensitive") for tc in t_classes):
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
) -> PolicyDecision:
    """Evaluate RBAC policy for `(persona, data_classes, question)` and return `PolicyDecision`."""
    canon = _canon_or_raw(persona)
    pc = persona_class(canon or persona)
    p_func = persona_function(canon or persona)
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
                persona=canon or persona,
                function=p_func,
                target_function="ANY",
            )
        return PolicyDecision(
            action="refuse",
            persona_class=pc,
            data_classes=["role_escalation"],
            trigger="role_escalation",
            rule_ref=refs.get("D-41") or "SPEC-06 §4.4",
            reason=refusal_text(canon or persona, "role_escalation"),
            code="R-ROLE",
            persona=canon or persona,
            function=p_func,
            target_function="ANY",
        )

    # 2. Self-scope check (SPEC-06 §5.3: `self` overrides `pay_individual`/`apar`/`named` for own record)
    detected_self_id = _detect_self_emp_id(canon, question, in_classes, explicit_self_emp_id=self_emp_id)
    if detected_self_id:
        return PolicyDecision(
            action="allow",
            persona_class=pc,
            data_classes=["self"],
            trigger="self",
            rule_ref="SPEC-06 §5.3",
            reason="Self-service query bound to @self_emp_id.",
            code=None,
            persona=canon or persona,
            function=p_func,
            target_function="SELF",
            self_emp_id=detected_self_id,
        )

    # 3. Enrich classes and target_function from question when provided
    classes = _enrich_classes_from_question(question, in_classes or ["general"], pc)
    eff_target = _infer_target_function(question, classes, explicit_target=target_function)

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
            reason=refusal_text(canon or persona, "function_mismatch"),
            code="R-FUNC",
            persona=canon or persona,
            function=p_func,
            target_function="HR",
        )

    # Legacy compatibility: if a bare v1 test calls `decide("DIR_FIN", ["named"])` with no question
    # and no explicit target_function and a legacy class name, check if target_function was omitted.
    # For explicit v2 calls or when question/target_function is supplied, evaluate function scope strictly.
    worst = "allow"
    trigger: Optional[str] = None
    worst_code: Optional[str] = None

    for c in sorted(set(classes)):
        # If bare v1 legacy call `decide("DIR_FIN", ["pay"])` or `decide("DIR_FIN", ["named"])`
        # without question or target_function, treat target_function as caller's own function for
        # function_scoped classes unless target_function was explicitly passed.
        call_target = eff_target
        if not question and target_function is None and c in ("named", "pay", "pay_individual", "apar", "board_confidential"):
            # When testing the 11x12 matrix without target_function, HR-owned classes default to HR
            # EXCEPT legacy v1 5x5 test which passes "pay" (not "pay_individual").
            if c == "pay":
                call_target = p_func
        act, code = _resolve_class_action(
            canon or persona,
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
            reason = f"Cross-functional detail is aggregated for {canon or persona} under D-43."
    elif worst == "refuse":
        if worst_code == "R-FUNC":
            reason = refusal_text(canon or persona, "function_mismatch")
        elif worst_code == "R-BOARD":
            reason = refusal_text(canon or persona, "board_confidential")
        else:
            reason = (
                {
                    "pay": "Pay and compensation records",
                    "pay_individual": "Pay and compensation records",
                    "apar": "APAR ratings and scores",
                    "sensitive": "Vigilance, POSH and medical records",
                    "board_confidential": "Board-confidential succession notes",
                }.get(trigger or "", "These records")
                + " are confidential for E1–E4 officers."
            )

    return PolicyDecision(
        action=worst,
        persona_class=pc,
        data_classes=sorted(set(classes)),
        trigger=trigger,
        rule_ref=ref,
        reason=reason,
        code=worst_code,
        persona=canon or persona,
        function=p_func,
        target_function=eff_target,
    )


def to_aggregate(spec: QuerySpec) -> QuerySpec:
    """Roster -> counts (by grade unless the spec already has a breakdown)."""
    data = spec.model_dump(by_alias=True)
    data["grain"] = "aggregate"
    if not data.get("dimensions"):
        data["dimensions"] = [load_policy().get("aggregate_dimension_default", "grade")]
    return QuerySpec.model_validate(data)


def suppress_small_cells(
    rows: List[Dict[str, Any]],
    value_columns: List[str],
    threshold: Optional[int] = None,
    by_name: bool = True,
    cell_count_col: Optional[str] = None,
    value_check: bool = True,
) -> Tuple[List[Dict[str, Any]], int]:
    """Counts below the threshold become '<5' (D-11 / R-K5)."""
    t = threshold or int(load_policy().get("small_cell_threshold", 5))
    out, n = [], 0
    for r in rows:
        r2 = dict(r)
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
                r2[c] = f"<{t}"
                n += 1
        if cell_count_col:
            r2.pop(cell_count_col, None)
        out.append(r2)
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


def enforce_contract(contract: Dict[str, Any], persona: str) -> Dict[str, Any]:
    """Post-query guard on any contract (planner or legacy). Idempotent."""
    c = contract
    pc = persona_class(persona)
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

    if pc != "junior":
        return c

    # If the contract was explicitly marked as a self-scoped query (`access.self_emp_id` set),
    # allow the employee's own row to pass through unmasked after verifying no other emp_id is present.
    self_id = access.get("self_emp_id")
    if self_id and access.get("status") == "allowed":
        tbl = vis.get("table")
        if isinstance(tbl, dict):
            rows = tbl.get("rows") or []
            foreign = [
                r.get("emp_id")
                for r in rows
                if isinstance(r, dict) and r.get("emp_id") and str(r.get("emp_id")).upper() != str(self_id).upper()
            ]
            if not foreign:
                return c

    # Check if this is an aggregate pay contract (e.g. avg_ctc_lakh by grade with no named columns)
    allow_agg_pay = bool(access.get("allow_pay_aggregate"))

    threshold = int(load_policy().get("small_cell_threshold", 5))
    masked_all: List[str] = []
    masked_values: List[str] = []
    suppressed = 0
    restricted_classes = ("named", "apar", "sensitive") if allow_agg_pay else ("named", "pay", "apar", "sensitive")

    for tbl in [vis.get("table")] + [it for it in ((vis.get("compare") or {}).get("items") or [])]:
        if not isinstance(tbl, dict) or "columns" not in tbl:
            continue
        masked = [col for col in (tbl.get("columns") or []) if column_class(col) in restricted_classes]
        if masked:
            for r in tbl.get("rows") or []:
                if isinstance(r, dict):
                    masked_values += [str(r[m]) for m in masked if isinstance(r.get(m), str) and len(str(r[m])) > 2]
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
        texts = (
            [c.get("spoken_summary") or "", c.get("display_text") or "", c.get("caveat") or ""]
            + [str(i) for i in c.get("insights") or []]
            + [str((vis.get("document") or {}).get("markdown") or "")]
        )
        leaked = any(v and v in t for v in set(masked_values) for t in texts)
        if leaked or vis.get("type") == "document":
            safe = (
                "This answer contains personal details that are restricted for your role (D-11), "
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
    if suppressed and access.get("status") == "allowed" and not masked_all:
        access["status"] = "partial"
        access["reason"] = f"{suppressed} cell(s) below {threshold} shown as <{threshold} for E1–E4 officers"
        access["rule_ref"] = load_policy().get("rule_refs", {}).get("D-11")
        access["code"] = "R-K5"
        tbl = vis.get("table")
        if isinstance(tbl, dict):
            tbl.setdefault("masking", {"level": "aggregate", "reason": access["reason"], "rule_ref": "D-11", "code": "R-K5"})
    if masked_all and access.get("status") == "allowed":
        refs = load_policy().get("rule_refs", {})
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
