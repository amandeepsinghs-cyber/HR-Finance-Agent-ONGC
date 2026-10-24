"""Persona Access Control Hook & Refusal Governance for Yukti AI.
Implements the persona permission matrix from UX Spec §2, §8, and
the refusal answers from official ONGC governance policies for D1–D6, P18–P20, M3, M4.
"""

from dataclasses import dataclass
import re
from typing import Any, Dict, Optional, Set

from app.config import GCP_PROJECT

CANONICAL_PERSONAS: tuple[str, ...] = (
    "CMD",
    "DIR_HR",
    "DIR_FIN",
    "E1_HR",
    "E2_HR",
    "E3_HR",
    "E4_HR",
    "E1_FIN",
    "E2_FIN",
    "E3_FIN",
    "E4_FIN",
)

# Personas allowed in answer contract schema (D-41: 11 personas)
ALL_PERSONAS_ORDERED: tuple[str, ...] = CANONICAL_PERSONAS
VALID_PERSONAS: Set[str] = set(CANONICAL_PERSONAS)

JUNIOR_HR_PERSONAS: frozenset[str] = frozenset({"E1_HR", "E2_HR", "E3_HR", "E4_HR"})
JUNIOR_FIN_PERSONAS: frozenset[str] = frozenset({"E1_FIN", "E2_FIN", "E3_FIN", "E4_FIN"})
JUNIOR_PERSONAS: frozenset[str] = JUNIOR_HR_PERSONAS | JUNIOR_FIN_PERSONAS
DIRECTOR_PERSONAS: frozenset[str] = frozenset({"DIR_HR", "DIR_FIN"})
SENIOR_PERSONAS: frozenset[str] = frozenset({"CMD", "DIR_HR", "DIR_FIN"})

# Persona alias normalization map
PERSONA_ALIASES = {
    # CMD
    "cmd": "CMD",
    "chairman": "CMD",
    "chairman & ceo": "CMD",
    "chairman and ceo": "CMD",
    "chairman & md": "CMD",
    "chairman and md": "CMD",
    "chairman & managing director": "CMD",
    "chairman and managing director": "CMD",
    "ceo": "CMD",
    "cmd_exec": "CMD",
    "arun": "CMD",
    "arun mehra": "CMD",
    # DIR_HR
    "dir hr": "DIR_HR",
    "dir-hr": "DIR_HR",
    "director (hr)": "DIR_HR",
    "director hr": "DIR_HR",
    "director - hr": "DIR_HR",
    "hr director": "DIR_HR",
    "director (human resources)": "DIR_HR",
    "dir_hr": "DIR_HR",
    "manish": "DIR_HR",
    "manish deshpande": "DIR_HR",
    # DIR_FIN
    "dir fin": "DIR_FIN",
    "dir-fin": "DIR_FIN",
    "director (finance)": "DIR_FIN",
    "director finance": "DIR_FIN",
    "director - finance": "DIR_FIN",
    "finance director": "DIR_FIN",
    "director (fin)": "DIR_FIN",
    "cfo": "DIR_FIN",
    "dir_fin": "DIR_FIN",
    "vivek": "DIR_FIN",
    "vivek rao": "DIR_FIN",
    # E1_HR
    "e1_hr": "E1_HR",
    "e1-hr": "E1_HR",
    "e1 hr": "E1_HR",
    "e1 · hr": "E1_HR",
    "hr_e1": "E1_HR",
    "hr-e1": "E1_HR",
    "hr e1": "E1_HR",
    "e1 hr officer": "E1_HR",
    "e1 hr executive": "E1_HR",
    "hr officer (e1)": "E1_HR",
    "dinesh deshmukh": "E1_HR",
    # E2_HR
    "e2_hr": "E2_HR",
    "e2-hr": "E2_HR",
    "e2 hr": "E2_HR",
    "e2 · hr": "E2_HR",
    "hr_e2": "E2_HR",
    "hr-e2": "E2_HR",
    "hr e2": "E2_HR",
    "e2 hr officer": "E2_HR",
    "e2 hr executive": "E2_HR",
    "hr executive (e2)": "E2_HR",
    "pooja verma": "E2_HR",
    "e1–e4 officer (hr)": "E2_HR",
    # E3_HR
    "e3_hr": "E3_HR",
    "e3-hr": "E3_HR",
    "e3 hr": "E3_HR",
    "e3 · hr": "E3_HR",
    "hr_e3": "E3_HR",
    "hr-e3": "E3_HR",
    "hr e3": "E3_HR",
    "e3 hr officer": "E3_HR",
    "e3 hr executive": "E3_HR",
    "senior hr executive (e3)": "E3_HR",
    "sr. hr executive (e3)": "E3_HR",
    "pooja pillai": "E3_HR",
    # E4_HR
    "e4_hr": "E4_HR",
    "e4-hr": "E4_HR",
    "e4 hr": "E4_HR",
    "e4 · hr": "E4_HR",
    "hr_e4": "E4_HR",
    "hr-e4": "E4_HR",
    "hr e4": "E4_HR",
    "e4 hr officer": "E4_HR",
    "e4 hr executive": "E4_HR",
    "dy. manager hr (e4)": "E4_HR",
    "deputy manager hr (e4)": "E4_HR",
    "aarti saikia": "E4_HR",
    # E1_FIN
    "e1_fin": "E1_FIN",
    "e1-fin": "E1_FIN",
    "e1 fin": "E1_FIN",
    "e1 · fin": "E1_FIN",
    "fin_e1": "E1_FIN",
    "fin-e1": "E1_FIN",
    "fin e1": "E1_FIN",
    "e1 finance": "E1_FIN",
    "e1 finance officer": "E1_FIN",
    "e1 accounts officer": "E1_FIN",
    "accounts officer (e1)": "E1_FIN",
    "ajay deshmukh": "E1_FIN",
    # E2_FIN
    "e2_fin": "E2_FIN",
    "e2-fin": "E2_FIN",
    "e2 fin": "E2_FIN",
    "e2 · fin": "E2_FIN",
    "fin_e2": "E2_FIN",
    "fin-e2": "E2_FIN",
    "fin e2": "E2_FIN",
    "e2 finance": "E2_FIN",
    "e2 finance officer": "E2_FIN",
    "e2 finance executive": "E2_FIN",
    "finance executive (e2)": "E2_FIN",
    "praveen nair": "E2_FIN",
    # E3_FIN
    "e3_fin": "E3_FIN",
    "e3-fin": "E3_FIN",
    "e3 fin": "E3_FIN",
    "e3 · fin": "E3_FIN",
    "fin_e3": "E3_FIN",
    "fin-e3": "E3_FIN",
    "fin e3": "E3_FIN",
    "e3 finance": "E3_FIN",
    "e3 finance officer": "E3_FIN",
    "e3 finance executive": "E3_FIN",
    "finance officer": "E3_FIN",
    "finance officer (e3)": "E3_FIN",
    "asha mishra": "E3_FIN",
    "rajesh kulkarni": "E3_FIN",
    "e1–e4 officer (finance)": "E3_FIN",
    # E4_FIN
    "e4_fin": "E4_FIN",
    "e4-fin": "E4_FIN",
    "e4 fin": "E4_FIN",
    "e4 · fin": "E4_FIN",
    "fin_e4": "E4_FIN",
    "fin-e4": "E4_FIN",
    "fin e4": "E4_FIN",
    "e4 finance": "E4_FIN",
    "e4 finance officer": "E4_FIN",
    "e4 finance executive": "E4_FIN",
    "dy. manager finance (e4)": "E4_FIN",
    "deputy manager finance (e4)": "E4_FIN",
    "santosh banerjee": "E4_FIN",
}

# The 11 refusal questions and their statutory definitions
REFUSAL_DEFINITIONS = {
    "D1": {
        "reason": "Individual compensation, basic pay, and allowances are strictly confidential personal data under ONGC CDA Rules and DPE guidelines.",
        "rule_ref": "ONGC CDA Rules 1994, Rule 5.0 (Confidentiality of Personal Information) & DPE Executive Compensation Guidelines.",
        "alternative": "Public executive pay scale bands (E0 to E9) and statutory DA/allowance brackets.",
        # D-10: CMD and Directors see individual pay; only E1–E4 are refused (D-11).
        "restricted_personas": set(JUNIOR_PERSONAS),
        "alternative_sql": f"""SELECT
    grade_id,
    designation,
    pay_scale_min_inr,
    pay_scale_max_inr,
    typical_residency_years
FROM `{GCP_PROJECT}.hrfin_silver.dim_grade`
WHERE LOWER(cadre) = 'executive'
ORDER BY level_order;"""
    },
    "D2": {
        "reason": "Unapproved draft transfer proposals and placement notes are non-final deliberative records exempt from disclosure prior to official notification by Director (HR).",
        "rule_ref": "ONGC Job Rotation and Transfer Policy (JRTP) Clause 11.0 (Confidentiality & Promulgation of Transfer Orders) & RTI Act Section 8(1)(i).",
        "alternative": "Station tenure guidelines (JRTP Clause 3.0) and aggregate count of Mumbai executives overdue for rotational transfer.",
        "restricted_personas": set(JUNIOR_PERSONAS),
        "alternative_sql": f"""SELECT
    grade_id,
    discipline_id,
    COUNT(DISTINCT emp_id) AS mumbai_executives_due_rotation
FROM `{GCP_PROJECT}.hrfin_gold.v_continuous_stay`
WHERE is_current_stay = TRUE
  AND cluster_id = 'CL-MUM'
  AND grade_id LIKE 'E%'
  AND continuous_stay_months >= 36
GROUP BY grade_id, discipline_id
ORDER BY grade_id, discipline_id;"""
    },
    "D3": {
        "reason": "Departmental Promotion Committee (DPC) deliberations, assessment rosters, and promotion panel recommendations are classified confidential records.",
        "rule_ref": "Modified Recruitment & Promotion Regulations 1980 / Service Rules 1995, Clause 8.0 (Confidentiality of DPC Proceedings & Sealed Cover).",
        "alternative": "Published promotion policy residency requirements and benchmark APAR eligibility criteria by grade.",
        "restricted_personas": set(JUNIOR_PERSONAS),
        "alternative_sql": f"""SELECT
    grade_id,
    designation,
    typical_residency_years,
    promotion_mode,
    dpc_evaluation_type
FROM `{GCP_PROJECT}.hrfin_silver.dim_grade`
WHERE LOWER(cadre) = 'executive'
ORDER BY level_order;"""
    },
    "D4": {
        "reason": "Field-level profitability statements and draft forward capital budget allocations are commercially sensitive operational data restricted to senior management.",
        "rule_ref": "Book of Delegated Powers (BDP 2015) Clause 8.0 & Corporate Commercial Information Protection Guidelines.",
        "alternative": "Company-wide gross revenues, standalone capital expenditure, and net profit from published annual accounts.",
        "restricted_personas": set(JUNIOR_PERSONAS),
        "alternative_sql": f"""SELECT
    fiscal_year,
    gross_revenue_inr_cr,
    total_capex_spent_inr_cr,
    pat_inr_cr
FROM `{GCP_PROJECT}.hrfin_gold.mart_corporate_performance`
WHERE fiscal_year IS NOT NULL
GROUP BY fiscal_year, gross_revenue_inr_cr, total_capex_spent_inr_cr, pat_inr_cr
ORDER BY fiscal_year DESC
LIMIT 5;"""
    },
    "D5": {
        "reason": "Bulk nominal employee rosters containing personal tenure and posting histories are restricted from disclosure to general staff to protect personal privacy.",
        "rule_ref": "ONGC IT Data Governance Policy & CDA Rules 1994, Rule 5.0.",
        "alternative": "Aggregated counts of Delhi executives possessing station tenure >= 5 years, grouped by grade band.",
        "restricted_personas": set(JUNIOR_PERSONAS),
        "alternative_sql": f"""SELECT
    grade_id,
    COUNT(DISTINCT emp_id) AS executives_ge_5yr_count
FROM `{GCP_PROJECT}.hrfin_gold.v_continuous_stay`
WHERE is_current_stay = TRUE
  AND wc_id = 'WC-DEL'
  AND grade_id LIKE 'E%'
  AND continuous_stay_months >= 60
GROUP BY grade_id
ORDER BY grade_id;"""
    },
    "D6": {
        "reason": "Vigilance inquiry records, preliminary investigation reports, and complaint dossiers are strictly classified and protected against unauthorized disclosure.",
        "rule_ref": "Central Vigilance Commission (CVC) Operating Manual & ONGC Vigilance Guidelines, Clause 7.0.",
        "alternative": "Standard procedure for lodging vigilance complaints and Whistle Blower Policy protections.",
        "restricted_personas": set(JUNIOR_PERSONAS),
        "alternative_sql": f"""SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `{GCP_PROJECT}.hrfin_docs.silver_chunks`
WHERE doc_id IN ('P2-01', 'Whistle Blower Policy') OR questions_served LIKE '%D6%'
ORDER BY doc_id, clause_ref
LIMIT 5;"""
    },
    "P18": {
        "reason": "Annual rotational transfer orders in draft proposal stage are privileged administrative deliberations pending formal approval by Director (HR) and CMD.",
        "rule_ref": "Job Rotation and Transfer Policy (JRTP) Clause 11.0 (Confidentiality & Promulgation of Transfer Orders).",
        "alternative": "Published JRTP rotation calendar, station tenure norms (Clause 3.0), and hard station service rules.",
        "restricted_personas": set(JUNIOR_PERSONAS),
        "alternative_sql": f"""SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `{GCP_PROJECT}.hrfin_docs.silver_chunks`
WHERE doc_id = 'JRTP' AND clause_ref IN ('Clause 3.0', 'Clause 9.0', 'Clause 11.0')
ORDER BY clause_ref;"""
    },
    "P19": {
        "reason": "The internal discretionary financial delegation matrix and reserved authorization limits for Whole-Time Directors are classified administrative records.",
        "rule_ref": "Book of Delegated Powers (BDP 2015) Clause 8.0 (Confidentiality & Exceptions).",
        "alternative": "Operational financial delegation limits assigned to Key Executives / Level-1 Asset Managers for day-to-day procurement.",
        "restricted_personas": set(JUNIOR_PERSONAS),
        "alternative_sql": f"""SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `{GCP_PROJECT}.hrfin_docs.silver_chunks`
WHERE doc_id = 'BDP summary' AND clause_ref IN ('Clause 2.0', 'Clause 3.0')
ORDER BY clause_ref;"""
    },
    "P20": {
        "reason": "Board agenda memoranda, internal valuation sheets, and commercial deliberations on asset divestment are strictly confidential Board documents.",
        "rule_ref": "Companies Act 2013 Section 118 / ONGC Board Secretariat Governance Norms.",
        "alternative": "Government policy guidelines for Discovered Small Fields (DSF) and the Production Enhancement Contract (PEC) framework for mature fields.",
        "restricted_personas": {"DIR_HR"} | set(JUNIOR_PERSONAS),
        "alternative_sql": f"""SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `{GCP_PROJECT}.hrfin_docs.silver_chunks`
WHERE doc_id IN ('G-07', 'BDP summary') OR questions_served LIKE '%P20%'
ORDER BY doc_id, clause_ref
LIMIT 5;"""
    },
    "M3": {
        "reason": "Individual compensation and annual performance appraisal ratings (APAR) for specific employees are strictly confidential personal records.",
        "rule_ref": "ONGC CDA Rules 1994, Rule 5.0 (Confidentiality of Personal Records) & Right to Privacy guidelines.",
        "alternative": "Official procedure for an officer to access their own appraisal and pay slip via Employee Self Service (ESS) portal.",
        # D-10: CMD and Directors see individual pay and APAR; only E1–E4 are refused (D-11).
        "restricted_personas": set(JUNIOR_PERSONAS),
        "alternative_sql": f"""SELECT
    grade_id,
    designation,
    pay_scale_min_inr,
    pay_scale_max_inr,
    typical_residency_years
FROM `{GCP_PROJECT}.hrfin_silver.dim_grade`
WHERE LOWER(cadre) = 'executive'
ORDER BY level_order;"""
    },
    "M4": {
        "reason": "Field-level profitability reports and individual field margin economics are restricted commercially sensitive operational data.",
        "rule_ref": "Book of Delegated Powers (BDP 2015) Clause 8.0 & Corporate Commercial Policy.",
        "alternative": "Standalone corporate revenue, gross operating profit (EBITDA), and total production figures from published annual accounts.",
        "restricted_personas": set(JUNIOR_PERSONAS),
        "alternative_sql": f"""SELECT
    fiscal_year,
    gross_revenue_inr_cr,
    ebitda_inr_cr,
    pat_inr_cr
FROM `{GCP_PROJECT}.hrfin_gold.mart_corporate_performance`
WHERE fiscal_year IS NOT NULL
GROUP BY fiscal_year, gross_revenue_inr_cr, ebitda_inr_cr, pat_inr_cr
ORDER BY fiscal_year DESC
LIMIT 5;"""
    }
}


# B3 (D-11 / S2): topic refusals that have no question in the original bank.
REFUSAL_DEFINITIONS["R-POSH"] = {
    "reason": "POSH complaints and Internal Committee proceedings are confidential under the POSH Act 2013.",
    "rule_ref": "Sexual Harassment of Women at Workplace Act 2013, Section 16 (confidentiality)",
    "alternative": "The POSH policy, the complaint procedure and the Internal Committee contacts for your station.",
    "restricted_personas": set(JUNIOR_PERSONAS),
    "alternative_sql": None,
}
REFUSAL_DEFINITIONS["R-MED"] = {
    "reason": "Individual medical and health records are confidential personal data.",
    "rule_ref": "ONGC Medical Attendance & Treatment Rules (confidentiality) · D-11",
    "alternative": "Aggregate medical-claim volumes and turnaround times by work centre.",
    "restricted_personas": set(JUNIOR_PERSONAS),
    "alternative_sql": None,
}


@dataclass
class AccessDecision:
    status: str  # "allowed", "partial", "refused"
    reason: Optional[str] = None
    rule_ref: Optional[str] = None
    alternative: Optional[str] = None
    alternative_sql: Optional[str] = None
    refusal_id: Optional[str] = None
    self_emp_id: Optional[str] = None
    code: Optional[str] = None


class UnknownPersona(ValueError):
    """P0.4 (SPEC-06 §4.4 rule 1): an unknown persona is an identity error (HTTP 401), never coerced."""


_JUNIOR_ALIAS_RE = re.compile(
    r"^(?:(hr|human\s*resources|fin|finance|accounts)[\s_\-·]*)?"
    r"e([1-4])"
    r"(?:[\s_\-·]*(hr|human\s*resources|fin|finance|accounts))?"
    r"(?:[\s_\-]+(?:officer|executive|exec|manager|dy\.?\s*manager|sr\.?\s*executive|senior\s*executive))?$",
    re.IGNORECASE,
)


def normalize_persona(persona: Optional[str]) -> str:
    """Normalizes a known persona id or alias into the 11 contract personas.

    P0.4 / P2H.1: unknown or empty values raise UnknownPersona instead of being coerced.
    """
    if not persona or not isinstance(persona, str) or not persona.strip():
        raise UnknownPersona("empty persona")
    cleaned = persona.strip()
    p_clean = cleaned.lower()
    if p_clean in PERSONA_ALIASES:
        return PERSONA_ALIASES[p_clean]
    if cleaned.upper() in VALID_PERSONAS:
        return cleaned.upper()
    m = _JUNIOR_ALIAS_RE.match(cleaned)
    if m:
        fn_prefix, grade_num, fn_suffix = m.group(1), m.group(2), m.group(3)
        fn_raw = (fn_prefix or fn_suffix or "").lower()
        if fn_raw.startswith("hr") or "human" in fn_raw:
            return f"E{grade_num}_HR"
        if fn_raw.startswith("fin") or fn_raw.startswith("acc"):
            return f"E{grade_num}_FIN"
    raise UnknownPersona(f"unknown persona {persona!r}")


_AGGREGATE_PAY_RE = re.compile(
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
    r")\b",
    re.IGNORECASE,
)


_SELF_QUERY_RE = re.compile(
    r"(?:"
    r"(?<![a-z])(?:my|mine|mera|meri|mere)(?:\s+(?:own|current|latest|monthly|annual|fy\d{2}|september|march|april|personal)){0,2}\s+"
    r"(?:salary|payslip|pay\s*slip|pay\s+components|pay\s+scale|ctc|basic\s*pay|da|hra|prp|gross\s*pay|net\s*pay|"
    r"leave|el|cl|hpl|balance|posting|postings|tenure|station|transfer|apar|rating|ratings|score|appraisal|"
    r"entitlement|entitlements|advance|advances|hba|car\s+advance|furniture|laptop|medical\s+claim\w*|reimbursement)(?![a-z])"
    r"|(?<![a-z])(?:how\s+long\s+have\s+i\s+been\s+posted|where\s+am\s+i\s+posted)(?![a-z])"
    r"|(?:मेरा|मेरी|मेरे)\s+(?:\S+\s+){0,2}(?:वेतन|सैलरी|छुट्टी|पोस्टिंग|स्थानांतरण|एपार|पात्रता)"
    r")",
    re.IGNORECASE,
)


def is_aggregate_pay_question(question: Optional[str]) -> bool:
    """Return True if `question` asks ONLY for cohort/grade average CTC or entry pay scale policy (closes BUG-07, BUG-28, R2-M1)."""
    if not question:
        return False
    q = question.strip()
    q_low = q.lower()
    from app.brain.rbac import _V2_AGG_PAY_RE, _mentions_individual_or_row_pay_target
    if not (_V2_AGG_PAY_RE.search(q) or _AGGREGATE_PAY_RE.search(q)):
        return False
    if re.search(
        r"\b(each|every|individual|reporting\s+officer|my\s+team|my\s+colleague\w*|"
        r"salary\s+of\s+(?:each|every|all)|pay\s+of\s+(?:each|every|all)|list\s+.*(?:salary|pay|ctc))\b",
        q_low,
    ):
        return False
    if _mentions_individual_or_row_pay_target(q):
        return False
    return True


def is_self_question(question: Optional[str], persona: Optional[str] = None) -> bool:
    """Return True if `question` is strictly a self-service query for the caller's own record (S1 / M3)."""
    if not question:
        return False
    q = question.strip()
    q_low = q.lower()
    if re.search(
        r"\b(reporting\s+officer|in\s+my\s+opinion|my\s+(?:team|colleague\w*|peer\w*|subordinate\w*|boss|manager|department|division|section|unit)|"
        r"(?:each|every|all)\s+(?:employee\w*|officer\w*|executive\w*|staff))\b",
        q_low,
    ):
        return False
    canon = None
    if persona:
        try:
            canon = normalize_persona(persona)
        except UnknownPersona:
            canon = None
    from app.auth import PERSONA_DIRECTORY

    my_emp_id = str((PERSONA_DIRECTORY.get(canon or "", {}) or {}).get("emp_id", "")).lower()
    emp_mentions = [m.lower() for m in re.findall(r"\bEMP-\d{4,6}\b", q, re.IGNORECASE)]
    if emp_mentions and any(m != my_emp_id for m in emp_mentions):
        return False
    for pid, info in PERSONA_DIRECTORY.items():
        if pid in ("DEMO_ADMIN", canon):
            continue
        other_name = str(info.get("display_name", "")).lower()
        if other_name and len(other_name) > 3 and other_name in q_low:
            return False

    if _SELF_QUERY_RE.search(q):
        return True
    if canon:
        info = PERSONA_DIRECTORY.get(canon, {})
        emp_id = str(info.get("emp_id", ""))
        disp = str(info.get("display_name", ""))
        if emp_id and emp_id.lower() in q_low:
            return True
        if disp and len(disp) > 3 and disp.lower() in q_low:
            return True
    return False


def check_access(persona: str, entry_id: Optional[str] = None, query: Optional[str] = None) -> AccessDecision:
    """Evaluates whether the given persona has clearance for an entry or query topic (S1, S2).

    Returns an AccessDecision object.
    """
    normalized_persona = normalize_persona(persona)

    # 1. Check if entry_id corresponds to a known refusal first (S1)
    root_id = entry_id.split("__")[0] if entry_id else None
    if root_id and root_id in REFUSAL_DEFINITIONS:
        ref_def = REFUSAL_DEFINITIONS[root_id]
        if normalized_persona == "DIR_FIN" and root_id in ("R-POSH", "R-MED"):
            return AccessDecision(
                status="partial",
                reason="Under D-43, Director (Finance) receives aggregate counts only (k >= 5) for POSH and medical records.",
                rule_ref="D-43 · " + ref_def["rule_ref"],
                alternative=ref_def["alternative"],
                alternative_sql=ref_def["alternative_sql"],
                refusal_id=root_id,
                code="R-SENS",
            )
        if normalized_persona in ref_def["restricted_personas"]:
            return AccessDecision(
                status="refused",
                reason=ref_def["reason"],
                rule_ref=ref_def["rule_ref"],
                alternative=ref_def["alternative"],
                alternative_sql=ref_def["alternative_sql"],
                refusal_id=root_id,
            )
        elif normalized_persona == "CMD":
            return AccessDecision(status="allowed")

    # 2. Check strict self-scope or aggregate-pay relaxation (only when no other-employee/team target is present)
    if query and is_self_question(query, normalized_persona):
        from app.auth import PERSONA_DIRECTORY

        self_id = PERSONA_DIRECTORY.get(normalized_persona, {}).get("emp_id")
        return AccessDecision(
            status="allowed",
            reason="Self-service query bound to @self_emp_id.",
            rule_ref="SPEC-06 §5.3",
            self_emp_id=self_id,
        )

    if query and is_aggregate_pay_question(query):
        return AccessDecision(
            status="allowed",
            reason="Aggregate pay / entry pay-scale query allowed across all personas (k >= 5).",
            rule_ref="SPEC-06 §5.1 · D-41",
        )

    # 2. Text / Query keyword heuristic for novel queries
    if query:
        q_low = query.lower()
        if normalized_persona in JUNIOR_PERSONAS:
            if "salary of my reporting officer" in q_low or ("salary" in q_low and "reporting officer" in q_low):
                d = REFUSAL_DEFINITIONS["D1"]
                return AccessDecision(
                    status="refused",
                    reason=d["reason"],
                    rule_ref=d["rule_ref"],
                    alternative=d["alternative"],
                    alternative_sql=d["alternative_sql"],
                    refusal_id="D1",
                    code="R-PAY",
                )
            # D-11 (B3): pay, APAR and vigilance/POSH/medical topics are refused for E1–E4, whatever the
            # wording (topic keywords live in app/brain/rbac_policy.yaml).
            from app.brain.rbac import topic_classes

            topics = topic_classes(query)
            if topics:
                q_l = query.lower()
                if "apar" in topics:
                    rid, code = "M3", "R-APAR"
                elif "pay" in topics:
                    rid, code = "D1", "R-PAY"
                elif "posh" in q_l or "harassment" in q_l:
                    rid, code = "R-POSH", "R-SENS"
                elif "medical" in q_l or "health" in q_l:
                    rid, code = "R-MED", "R-SENS"
                else:
                    rid, code = "D6", "R-SENS"
                d = REFUSAL_DEFINITIONS[rid]
                return AccessDecision(
                    status="refused",
                    reason=d["reason"],
                    rule_ref=d["rule_ref"] + " · D-11",
                    alternative=d["alternative"],
                    alternative_sql=d["alternative_sql"],
                    refusal_id=rid,
                    code=code,
                )
            # Check for draft transfer list
            if "draft transfer list" in q_low or "draft fy27 transfer order" in q_low:
                d = REFUSAL_DEFINITIONS["D2"]
                return AccessDecision(
                    status="refused",
                    reason=d["reason"],
                    rule_ref=d["rule_ref"],
                    alternative=d["alternative"],
                    alternative_sql=d["alternative_sql"],
                    refusal_id="D2",
                )
            # Check for DPC promotion list
            if "getting promoted" in q_low and "dpc" in q_low:
                d = REFUSAL_DEFINITIONS["D3"]
                return AccessDecision(
                    status="refused",
                    reason=d["reason"],
                    rule_ref=d["rule_ref"],
                    alternative=d["alternative"],
                    alternative_sql=d["alternative_sql"],
                    refusal_id="D3",
                )
            # Check for field loss / profitability
            if any(k in q_low for k in ["which fields are loss-making", "loss-making fields", "fields lost money", "fields made losses", "profitable and which made losses", "field profitability", "field p&l"]):
                d = REFUSAL_DEFINITIONS["D4"]
                return AccessDecision(
                    status="refused",
                    reason=d["reason"],
                    rule_ref=d["rule_ref"],
                    alternative=d["alternative"],
                    alternative_sql=d["alternative_sql"],
                    refusal_id="D4",
                )
            # Check for nominal employee roster
            if "list all employees in delhi with more than 5 years" in q_low:
                d = REFUSAL_DEFINITIONS["D5"]
                return AccessDecision(
                    status="refused",
                    reason=d["reason"],
                    rule_ref=d["rule_ref"],
                    alternative=d["alternative"],
                    alternative_sql=d["alternative_sql"],
                    refusal_id="D5",
                    code="R-NAMED",
                )
            # Check for vigilance inquiry
            if "vigilance inquiry" in q_low or "under vigilance" in q_low:
                d = REFUSAL_DEFINITIONS["D6"]
                return AccessDecision(
                    status="refused",
                    reason=d["reason"],
                    rule_ref=d["rule_ref"],
                    alternative=d["alternative"],
                    alternative_sql=d["alternative_sql"],
                    refusal_id="D6",
                    code="R-SENS",
                )
            # Check for director limits
            if "financial limits for directors" in q_low:
                d = REFUSAL_DEFINITIONS["P19"]
                return AccessDecision(
                    status="refused",
                    reason=d["reason"],
                    rule_ref=d["rule_ref"],
                    alternative=d["alternative"],
                    alternative_sql=d["alternative_sql"],
                    refusal_id="P19",
                )
        if normalized_persona == "DIR_HR" or normalized_persona in JUNIOR_PERSONAS:
            if "divesting marginal fields" in q_low or "divestment" in q_low and "marginal fields" in q_low:
                d = REFUSAL_DEFINITIONS["P20"]
                return AccessDecision(
                    status="refused",
                    reason=d["reason"],
                    rule_ref=d["rule_ref"],
                    alternative=d["alternative"],
                    alternative_sql=d["alternative_sql"],
                    refusal_id="P20",
                    code="R-BOARD",
                )

    return AccessDecision(status="allowed")
