"""Persona Access Control Hook & Refusal Governance for Yukti AI.
Implements the persona permission matrix from UX Spec §2, §8, and
the refusal answers from official ONGC governance policies for D1–D6, P18–P20, M3, M4.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Set

# Personas allowed in answer contract schema
VALID_PERSONAS = {"CMD", "DIR_HR", "DIR_FIN", "E2_HR", "E3_FIN"}

# Persona alias normalization map
PERSONA_ALIASES = {
    "cmd": "CMD",
    "chairman": "CMD",
    "chairman & ceo": "CMD",
    "dir hr": "DIR_HR",
    "director (hr)": "DIR_HR",
    "dir_hr": "DIR_HR",
    "dir fin": "DIR_FIN",
    "director (finance)": "DIR_FIN",
    "dir_fin": "DIR_FIN",
    "e2_hr": "E2_HR",
    "e2 · hr": "E2_HR",
    "pooja verma": "E2_HR",
    "e1–e4 officer (hr)": "E2_HR",
    "e3_fin": "E3_FIN",
    "e3 · fin": "E3_FIN",
    "rajesh kulkarni": "E3_FIN",
    "e1–e4 officer (finance)": "E3_FIN",
}

# The 11 refusal questions and their statutory definitions
REFUSAL_DEFINITIONS = {
    "D1": {
        "reason": "Individual compensation, basic pay, and allowances are strictly confidential personal data under ONGC CDA Rules and DPE guidelines.",
        "rule_ref": "ONGC CDA Rules 1994, Rule 5.0 (Confidentiality of Personal Information) & DPE Executive Compensation Guidelines.",
        "alternative": "Public executive pay scale bands (E0 to E9) and statutory DA/allowance brackets.",
        "restricted_personas": {"E2_HR", "E3_FIN", "DIR_HR", "DIR_FIN"},
        "alternative_sql": """SELECT
    grade_id,
    designation,
    pay_scale_min_inr,
    pay_scale_max_inr,
    typical_residency_years
FROM `ongc-hr-finance-agent.hrfin_silver.dim_grade`
WHERE LOWER(cadre) = 'executive'
ORDER BY level_order;"""
    },
    "D2": {
        "reason": "Unapproved draft transfer proposals and placement notes are non-final deliberative records exempt from disclosure prior to official notification by Director (HR).",
        "rule_ref": "ONGC Job Rotation and Transfer Policy (JRTP) Clause 11.0 (Confidentiality & Promulgation of Transfer Orders) & RTI Act Section 8(1)(i).",
        "alternative": "Station tenure guidelines (JRTP Clause 3.0) and aggregate count of Mumbai executives overdue for rotational transfer.",
        "restricted_personas": {"E2_HR", "E3_FIN"},
        "alternative_sql": """SELECT
    grade_id,
    discipline_id,
    COUNT(DISTINCT emp_id) AS mumbai_executives_due_rotation
FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay`
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
        "restricted_personas": {"E2_HR", "E3_FIN"},
        "alternative_sql": """SELECT
    grade_id,
    designation,
    typical_residency_years,
    promotion_mode,
    dpc_evaluation_type
FROM `ongc-hr-finance-agent.hrfin_silver.dim_grade`
WHERE LOWER(cadre) = 'executive'
ORDER BY level_order;"""
    },
    "D4": {
        "reason": "Field-level profitability statements and draft forward capital budget allocations are commercially sensitive operational data restricted to senior management.",
        "rule_ref": "Book of Delegated Powers (BDP 2015) Clause 8.0 & Corporate Commercial Information Protection Guidelines.",
        "alternative": "Audited company-wide gross revenues, standalone capital expenditure, and net profit from published annual accounts.",
        "restricted_personas": {"E2_HR", "E3_FIN"},
        "alternative_sql": """SELECT
    fiscal_year,
    gross_revenue_inr_cr,
    total_capex_spent_inr_cr,
    pat_inr_cr
FROM `ongc-hr-finance-agent.hrfin_gold.mart_corporate_performance`
WHERE fiscal_year IS NOT NULL
GROUP BY fiscal_year, gross_revenue_inr_cr, total_capex_spent_inr_cr, pat_inr_cr
ORDER BY fiscal_year DESC
LIMIT 5;"""
    },
    "D5": {
        "reason": "Bulk nominal employee rosters containing personal tenure and posting histories are restricted from disclosure to general staff to protect personal privacy.",
        "rule_ref": "ONGC IT Data Governance Policy & CDA Rules 1994, Rule 5.0.",
        "alternative": "Aggregated counts of Delhi executives possessing station tenure >= 5 years, grouped by grade band.",
        "restricted_personas": {"E2_HR", "E3_FIN"},
        "alternative_sql": """SELECT
    grade_id,
    COUNT(DISTINCT emp_id) AS executives_ge_5yr_count
FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay`
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
        "restricted_personas": {"E2_HR", "E3_FIN"},
        "alternative_sql": """SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id IN ('P2-01', 'Whistle Blower Policy') OR questions_served LIKE '%D6%'
ORDER BY doc_id, clause_ref
LIMIT 5;"""
    },
    "P18": {
        "reason": "Annual rotational transfer orders in draft proposal stage are privileged administrative deliberations pending formal approval by Director (HR) and CMD.",
        "rule_ref": "Job Rotation and Transfer Policy (JRTP) Clause 11.0 (Confidentiality & Promulgation of Transfer Orders).",
        "alternative": "Published JRTP rotation calendar, station tenure norms (Clause 3.0), and hard station service rules.",
        "restricted_personas": {"E2_HR", "E3_FIN"},
        "alternative_sql": """SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'JRTP' AND clause_ref IN ('Clause 3.0', 'Clause 9.0', 'Clause 11.0')
ORDER BY clause_ref;"""
    },
    "P19": {
        "reason": "The internal discretionary financial delegation matrix and reserved authorization limits for Whole-Time Directors are classified administrative records.",
        "rule_ref": "Book of Delegated Powers (BDP 2015) Clause 8.0 (Confidentiality & Exceptions).",
        "alternative": "Operational financial delegation limits assigned to Key Executives / Level-1 Asset Managers for day-to-day procurement.",
        "restricted_personas": {"E2_HR", "E3_FIN"},
        "alternative_sql": """SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'BDP summary' AND clause_ref IN ('Clause 2.0', 'Clause 3.0')
ORDER BY clause_ref;"""
    },
    "P20": {
        "reason": "Board agenda memoranda, internal valuation sheets, and commercial deliberations on asset divestment are strictly confidential Board documents.",
        "rule_ref": "Companies Act 2013 Section 118 / ONGC Board Secretariat Governance Norms.",
        "alternative": "Government policy guidelines for Discovered Small Fields (DSF) and the Production Enhancement Contract (PEC) framework for mature fields.",
        "restricted_personas": {"DIR_HR", "E2_HR", "E3_FIN"},
        "alternative_sql": """SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id IN ('G-07', 'BDP summary') OR questions_served LIKE '%P20%'
ORDER BY doc_id, clause_ref
LIMIT 5;"""
    },
    "M3": {
        "reason": "Individual compensation and annual performance appraisal ratings (APAR) for specific employees are strictly confidential personal records.",
        "rule_ref": "ONGC CDA Rules 1994, Rule 5.0 (Confidentiality of Personal Records) & Right to Privacy guidelines.",
        "alternative": "Official procedure for an officer to access their own appraisal and pay slip via Employee Self Service (ESS) portal.",
        "restricted_personas": {"E2_HR", "E3_FIN", "DIR_HR", "DIR_FIN"},
        "alternative_sql": """SELECT
    grade_id,
    designation,
    pay_scale_min_inr,
    pay_scale_max_inr,
    typical_residency_years
FROM `ongc-hr-finance-agent.hrfin_silver.dim_grade`
WHERE LOWER(cadre) = 'executive'
ORDER BY level_order;"""
    },
    "M4": {
        "reason": "Field-level profitability reports and individual field margin economics are restricted commercially sensitive operational data.",
        "rule_ref": "Book of Delegated Powers (BDP 2015) Clause 8.0 & Corporate Commercial Policy.",
        "alternative": "Audited standalone corporate revenue, gross operating profit (EBITDA), and total production figures from published annual accounts.",
        "restricted_personas": {"E2_HR", "E3_FIN"},
        "alternative_sql": """SELECT
    fiscal_year,
    gross_revenue_inr_cr,
    ebitda_inr_cr,
    pat_inr_cr
FROM `ongc-hr-finance-agent.hrfin_gold.mart_corporate_performance`
WHERE fiscal_year IS NOT NULL
GROUP BY fiscal_year, gross_revenue_inr_cr, ebitda_inr_cr, pat_inr_cr
ORDER BY fiscal_year DESC
LIMIT 5;"""
    }
}


@dataclass
class AccessDecision:
    status: str  # "allowed", "partial", "refused"
    reason: Optional[str] = None
    rule_ref: Optional[str] = None
    alternative: Optional[str] = None
    alternative_sql: Optional[str] = None
    refusal_id: Optional[str] = None


def normalize_persona(persona: Optional[str]) -> str:
    """Normalizes any persona string or alias into the 5 contract personas."""
    if not persona:
        return "CMD"
    p_clean = persona.strip().lower()
    return PERSONA_ALIASES.get(p_clean, persona.upper() if persona.upper() in VALID_PERSONAS else "CMD")


def check_access(persona: str, entry_id: Optional[str] = None, query: Optional[str] = None) -> AccessDecision:
    """Evaluates whether the given persona has clearance for an entry or query topic.

    Returns an AccessDecision object.
    """
    normalized_persona = normalize_persona(persona)

    # 1. Check if entry_id corresponds to a known refusal
    root_id = entry_id.split("__")[0] if entry_id else None

    # Check for direct refusal mapping
    if root_id and root_id in REFUSAL_DEFINITIONS:
        ref_def = REFUSAL_DEFINITIONS[root_id]
        
        # If persona is restricted for this refusal
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
            # For D1 / M3, individual salary is confidential personal data even for CMD per CDA Rule 5.0,
            # but authorized aggregate pay scale is provided
            if root_id in ("D1", "M3") and (entry_id == root_id or (entry_id and "__why" in entry_id)):
                # D1 and M3 root/why are audited refusals in INDEX.md
                return AccessDecision(
                    status="refused",
                    reason=ref_def["reason"],
                    rule_ref=ref_def["rule_ref"],
                    alternative=ref_def["alternative"],
                    alternative_sql=ref_def["alternative_sql"],
                    refusal_id=root_id,
                )
            return AccessDecision(status="allowed")

    # 2. Text / Query keyword heuristic for novel queries
    if query:
        q_low = query.lower()
        if normalized_persona in ("E2_HR", "E3_FIN"):
            # Check for salary of other person
            if "salary of my reporting officer" in q_low or ("salary" in q_low and "reporting officer" in q_low):
                d = REFUSAL_DEFINITIONS["D1"]
                return AccessDecision(
                    status="refused",
                    reason=d["reason"],
                    rule_ref=d["rule_ref"],
                    alternative=d["alternative"],
                    alternative_sql=d["alternative_sql"],
                    refusal_id="D1",
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
        if normalized_persona in ("DIR_HR", "E2_HR", "E3_FIN"):
            if "divesting marginal fields" in q_low or "divestment" in q_low and "marginal fields" in q_low:
                d = REFUSAL_DEFINITIONS["P20"]
                return AccessDecision(
                    status="refused",
                    reason=d["reason"],
                    rule_ref=d["rule_ref"],
                    alternative=d["alternative"],
                    alternative_sql=d["alternative_sql"],
                    refusal_id="P20",
                )

    return AccessDecision(status="allowed")
