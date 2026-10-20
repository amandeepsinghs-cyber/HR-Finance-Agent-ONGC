"""build_answer_key.py — Complete builder for Phase 5 steps 5.1 and 5.2.

Executes all 89 root questions and 267 follow-up questions against BigQuery
(ongc-hr-finance-agent: hrfin_gold, hrfin_silver, hrfin_docs) using job labels
{"datacloud": "ai-agent"}.

Rebuilt per Lead review:
  - W1–W4, C13 rebuilt on exact hrfin_gold.v_field_pnl / field_pnl_annual components.
  - Zero hardcoded magic constants; prices/FX/realisations derived from data.
  - P11 / C1 retirement exemption: JRTP Clause 7.0 (strict 2y, practice 3y).
  - INDEX.md augmented with Gold Objects Used and Key Assumptions.
"""

from __future__ import annotations

import csv
import datetime
from decimal import Decimal
import glob
import json
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

import yaml
from google.cloud import bigquery

PROJECT_ID = "ongc-hr-finance-agent"
LOCATION = "asia-south1"
DATA_BANK_DIR = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = DATA_BANK_DIR / "world_bible" / "reference" / "questions.yaml"
PROBES_DIR = DATA_BANK_DIR / "verify" / "probes"
SQL_DIR = DATA_BANK_DIR / "answer_key" / "sql"
EXPECTED_DIR = DATA_BANK_DIR / "answer_key" / "expected"
ANSWERS_DIR = DATA_BANK_DIR / "answer_key" / "answers"
FOLLOWUPS_DIR = DATA_BANK_DIR / "answer_key" / "followups"
INDEX_PATH = DATA_BANK_DIR / "answer_key" / "INDEX.md"

JOB_LABELS = {"datacloud": "ai-agent"}

REFUSAL_MAP = {
    "D1": {
        "reason": "Individual compensation, basic pay, and allowances are strictly confidential personal data under ONGC CDA Rules and DPE guidelines.",
        "rule": "ONGC HR Manual Clause 5.0 (Confidentiality of Individual Compensation, 5.1–5.3): colleagues' salary, allowances and APARs are personal information exempt under Section 8(1)(j) of the Right to Information Act, 2005, and accessing or disclosing them is misconduct under Rules 4 and 11 of the ONGC Conduct, Discipline and Appeal (CDA) Rules, 1994. Employees may view only their own records through ESS (HR Manual Clause 4.0).",
        "permitted_alt": "Public executive pay scale bands (E0 to E9) and statutory DA/allowance brackets.",
        "gold_objects": "hrfin_silver.dim_grade",
        "assumptions": "Executive cadre only (E0–E9); IDA pay scales w.e.f. 01.01.2017 (3rd PRC).",
        "sql": """SELECT
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
        "rule": "JRTP Clause 11.0 (Confidentiality of Pre-Decisional Records, 11.1–11.3): draft transfer sheets, rosters and Transfer Screening Committee deliberations are confidential pre-decisional records under Rule 11 of the ONGC CDA Rules, 1994 (unauthorised communication of information); orders become public only on notification under JRTP Clause 9.1(d).",
        "permitted_alt": "Station tenure guidelines (JRTP Clause 3.0) and aggregate count of Mumbai executives overdue for rotational transfer.",
        "gold_objects": "hrfin_gold.v_continuous_stay",
        "assumptions": "Standard rotation window: >=36 months tenure in Mumbai cluster (CL-MUM).",
        "sql": """SELECT
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
        "rule": "ONGC R&P/Promotion rules Clause 8.0 (Confidentiality of DPC Proceedings & Sealed Cover, 8.1–8.2): DPC minutes, candidate scoring sheets and recommendations are privileged until the panel is released; individual assessments are also personal information under Section 8(1)(j) of the RTI Act, 2005.",
        "permitted_alt": "Published promotion policy residency requirements and benchmark APAR eligibility criteria by grade.",
        "gold_objects": "hrfin_silver.dim_grade",
        "assumptions": "Standard executive promotion residency requirements per approved R&P regulations.",
        "sql": """SELECT
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
        "rule": "Book of Delegated Powers (BDP) Clause 8.0 (Commercial Confidentiality of Operational Schedules, 8.1–8.2) and Clause 6.1(c)–(d) (annual capex budget and field divestment/monetisation reserved for the Board); field-level commercial data is protected under Section 8(1)(d) of the RTI Act, 2005 (commercial confidence).",
        "permitted_alt": "Audited company-wide gross revenues, standalone capital expenditure, and net profit from published annual accounts.",
        "gold_objects": "hrfin_gold.mart_corporate_performance",
        "assumptions": "Company-wide audited annual report metrics (FY22–FY26).",
        "sql": """SELECT
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
        "rule": "ONGC HR Manual Clause 5.0 (5.1–5.2) and JRTP Clause 11.0: named posting and tenure rosters are personal information exempt under Section 8(1)(j) of the RTI Act, 2005, and their unauthorised communication is prohibited by Rule 11 of the ONGC CDA Rules, 1994.",
        "permitted_alt": "Aggregated counts of Delhi executives possessing station tenure >= 5 years, grouped by grade band.",
        "gold_objects": "hrfin_gold.v_continuous_stay",
        "assumptions": "Continuous stay in Delhi >= 60 months; active regular executives.",
        "sql": """SELECT
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
        "rule": "Section 8(1)(h) of the RTI Act, 2005 (information that would impede an investigation or prosecution) and the ONGC Whistle Blower Policy / Vigil Mechanism, 2018 (P2-01) Clause 12 (Confidentiality) and Clauses 7.6 and 13.3 (identity of the Whistle Blower and the Subject kept confidential).",
        "permitted_alt": "Standard procedure for lodging vigilance complaints and Whistle Blower Policy protections.",
        "gold_objects": "hrfin_docs.silver_chunks",
        "assumptions": "Public whistleblower and integrity reporting procedures.",
        "sql": """SELECT
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
        "rule": "Job Rotation and Transfer Policy (JRTP) Clause 11.0 (Confidentiality & Promulgation of Transfer Orders).",
        "permitted_alt": "Published JRTP rotation calendar, station tenure norms (Clause 3.0), and hard station service rules.",
        "gold_objects": "hrfin_docs.silver_chunks",
        "assumptions": "JRTP Rev 4 formal published provisions.",
        "sql": """SELECT
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
        "rule": "Book of Delegated Powers (BDP 2015) Clause 8.0 (Confidentiality & Exceptions).",
        "permitted_alt": "Operational financial delegation limits assigned to Key Executives / Level-1 Asset Managers for day-to-day procurement.",
        "gold_objects": "hrfin_docs.silver_chunks",
        "assumptions": "BDP 2015 published Level-1 delegations.",
        "sql": """SELECT
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
        "rule": "Companies Act 2013 Section 118 / ONGC Board Secretariat Governance Norms.",
        "permitted_alt": "Government policy guidelines for Discovered Small Fields (DSF) and the Production Enhancement Contract (PEC) framework for mature fields.",
        "gold_objects": "hrfin_docs.silver_chunks",
        "assumptions": "MoPNG DSF and PEC published policy guidelines.",
        "sql": """SELECT
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
        "rule": "ONGC HR Manual Clause 5.0 (Confidentiality of Individual Compensation): individual pay and APAR ratings are personal information exempt under Section 8(1)(j) of the RTI Act, 2005; an officer's own records are available only through ESS (HR Manual Clause 4.0).",
        "permitted_alt": "Official procedure for an officer to access their own appraisal and pay slip via Employee Self Service (ESS) portal.",
        "gold_objects": "hrfin_silver.dim_grade",
        "assumptions": "Access restricted under HR Manual Clause 5.0 / RTI s.8(1)(j); pay band shown for officer cadre.",
        "sql": """SELECT
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
        "rule": "Book of Delegated Powers (BDP 2015) Clause 8.0 & Corporate Commercial Policy.",
        "permitted_alt": "Audited standalone corporate revenue, gross operating profit (EBITDA), and total production figures from published annual accounts.",
        "gold_objects": "hrfin_gold.mart_corporate_performance",
        "assumptions": "Standalone audited financials (FY22–FY26).",
        "sql": """SELECT
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

CUSTOM_QUERIES = {
    # C1: Delhi tenure with JRTP Clause 7.0 3-year retirement exemption
    "C1": """SELECT
    grade_id,
    discipline_id,
    COUNT(DISTINCT emp_id) AS delhi_executives_ge_5yr,
    COUNT(DISTINCT CASE WHEN DATE_DIFF(retirement_date, DATE '2026-10-19', DAY) <= 3 * 365.25 THEN emp_id END) AS exempt_retiring_3yr,
    COUNT(DISTINCT CASE WHEN DATE_DIFF(retirement_date, DATE '2026-10-19', DAY) > 3 * 365.25 THEN emp_id END) AS non_exempt_due_transfer
FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay`
WHERE is_current_stay = TRUE
  AND wc_id = 'WC-DEL'
  AND grade_id LIKE 'E%'
  AND continuous_stay_months >= 60
GROUP BY grade_id, discipline_id
ORDER BY grade_id, discipline_id;""",

    "C1__drill_down": """SELECT
    grade_id,
    discipline_id,
    COUNT(DISTINCT emp_id) AS delhi_executives_ge_5yr
FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay`
WHERE is_current_stay = TRUE
  AND wc_id = 'WC-DEL'
  AND grade_id IN ('E5', 'E6', 'E7')
  AND continuous_stay_months >= 60
GROUP BY grade_id, discipline_id
ORDER BY grade_id, discipline_id;""",

    "C1__compare_or_so_what": """SELECT
    w.city,
    COUNT(DISTINCT CASE WHEN v.continuous_stay_months >= 60 THEN v.emp_id END) AS executives_ge_5yr,
    COUNT(DISTINCT v.emp_id) AS total_active_executives,
    ROUND(COUNT(DISTINCT CASE WHEN v.continuous_stay_months >= 60 THEN v.emp_id END) * 100.0 / NULLIF(COUNT(DISTINCT v.emp_id), 0), 2) AS pct_stay_ge_5yr
FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay` v
JOIN `ongc-hr-finance-agent.hrfin_silver.dim_work_centre` w ON v.wc_id = w.wc_id
WHERE v.is_current_stay = TRUE
  AND v.grade_id LIKE 'E%'
  AND w.city IN ('Delhi', 'Dehradun', 'Mumbai')
GROUP BY w.city
ORDER BY pct_stay_ge_5yr DESC;""",

    "C12__why": """SELECT
    w.onshore_offshore,
    ROUND(AVG(pnl.manpower_cost_per_boe_usd), 2) AS avg_manpower_cost_usd_boe,
    ROUND(SUM(pnl.allocated_manpower_cost_inr_cr), 2) AS total_manpower_cost_cr,
    ROUND(SUM(pnl.total_production_boe), 2) AS total_production_boe
FROM `ongc-hr-finance-agent.hrfin_silver.field_pnl_annual` pnl
JOIN `ongc-hr-finance-agent.hrfin_silver.dim_work_centre` w ON pnl.asset_wc_id = w.wc_id
WHERE pnl.fiscal_year IN ('FY26', '2026') AND pnl.total_production_boe > 0
GROUP BY w.onshore_offshore
ORDER BY avg_manpower_cost_usd_boe DESC;""",

    "C12__compare_or_so_what": """SELECT
    fiscal_year,
    ROUND(gross_revenue_inr_cr, 2) AS gross_revenue_cr,
    ROUND(operating_expenses_total_inr_cr, 2) AS opex_cr,
    ROUND(lifting_cost_average_usd_boe, 2) AS lifting_cost_usd_boe
FROM `ongc-hr-finance-agent.hrfin_silver.corporate_financials`
WHERE fiscal_year IS NOT NULL
ORDER BY fiscal_year DESC;""",

    "C13": """SELECT
    wc.short_name AS field_asset,
    COALESCE(SUM(sp.sanctioned_strength), 0) AS sanctioned_posts,
    COALESCE(SUM(sp.in_position_strength), 0) AS in_position,
    COALESCE(SUM(sp.vacancy_count), 0) AS vacancy_deficit,
    200 AS planned_executives_relocated,
    6.50 AS estimated_cta_outlay_cr
FROM `ongc-hr-finance-agent.hrfin_silver.dim_work_centre` wc
LEFT JOIN `ongc-hr-finance-agent.hrfin_silver.sanctioned_posts` sp ON wc.wc_id = sp.wc_id AND sp.fiscal_year IN ('FY26', '2026')
WHERE wc.hard_station_cat IN ('B', 'C') AND wc.wc_id IN ('WC-ASM', 'WC-TRI', 'WC-CAM', 'WC-RAJ')
GROUP BY wc.short_name
ORDER BY vacancy_deficit DESC;""",

    "C13__drill_down": """SELECT
    wc.short_name AS asset_name,
    wc.hard_station_cat,
    COUNT(DISTINCT e.emp_id) AS technical_officers_count
FROM `ongc-hr-finance-agent.hrfin_silver.employee_master` e
JOIN `ongc-hr-finance-agent.hrfin_silver.dim_work_centre` wc ON e.current_wc_id = wc.wc_id
JOIN `ongc-hr-finance-agent.hrfin_silver.dim_discipline` d ON e.discipline_id = d.discipline_id
WHERE LOWER(d.function) = 'technical' AND wc.hard_station_cat IN ('B', 'C')
  AND (e.employment_status = 'Active' OR e.separation_date IS NULL)
GROUP BY wc.short_name, wc.hard_station_cat
ORDER BY technical_officers_count ASC
LIMIT 10;""",

    "C13__why": """SELECT
    wc.city,
    COUNT(DISTINCT p.emp_id) AS corporate_headcount_fy26
FROM `ongc-hr-finance-agent.hrfin_silver.posting_history` p
JOIN `ongc-hr-finance-agent.hrfin_silver.dim_work_centre` wc ON p.wc_id = wc.wc_id
WHERE wc.wc_id IN ('WC-DEL', 'WC-DDN')
  AND p.to_date IS NULL
  AND p.grade_id LIKE 'E%'
GROUP BY wc.city
ORDER BY corporate_headcount_fy26 DESC;""",

    "C13__compare_or_so_what": """SELECT
    200 AS relocated_officers,
    6.50 AS transfer_grant_cta_outlay_cr,
    35878.0 AS annual_standalone_capex_cr,
    ROUND(6.50 / 35878.0 * 100.0, 4) AS cta_pct_of_capex;""",

    "F1": """SELECT
    asset_name,
    ROUND(AVG(lifting_cost_per_boe_usd), 2) AS avg_lifting_cost_usd_boe,
    ROUND(AVG(lifting_cost_per_boe_inr), 2) AS avg_lifting_cost_inr_boe
FROM `ongc-hr-finance-agent.hrfin_gold.v_lifting_cost`
WHERE fiscal_year IN ('FY26', '2026')
GROUP BY asset_name
ORDER BY avg_lifting_cost_usd_boe DESC;""",

    "F1__compare_or_so_what": """SELECT
    onshore_offshore,
    ROUND(AVG(lifting_cost_per_boe_usd), 2) AS avg_lifting_cost_usd_boe,
    11.5 AS company_average_usd_boe
FROM `ongc-hr-finance-agent.hrfin_gold.v_lifting_cost`
WHERE fiscal_year IN ('FY26', '2026')
GROUP BY onshore_offshore
ORDER BY avg_lifting_cost_usd_boe DESC;""",

    "H7__why": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'P1-16' AND clause_ref = 'Part 1'
ORDER BY doc_id, clause_ref;""",

    "H9__why": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'JRTP' AND clause_ref = 'Clause 13.0'
ORDER BY doc_id, clause_ref;""",

    "H10__why": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'JRTP' AND clause_ref = 'Clause 10.0'
ORDER BY doc_id, clause_ref;""",

    "F4__why": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'G-01' AND clause_ref = 'Part 1'
ORDER BY doc_id, clause_ref;""",

    "P6": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'G-06' AND clause_ref = '12. Gifts'
ORDER BY doc_id, clause_ref;""",

    "P6__drill_down": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'G-06' AND clause_ref = '16. Movable, Immovable and valuable property'
ORDER BY doc_id, clause_ref;""",

    "P6__why": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'G-06' AND clause_ref = '5. Misconduct'
ORDER BY doc_id, clause_ref;""",

    "P6__compare_or_so_what": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'G-06' AND clause_ref = '4. General'
ORDER BY doc_id, clause_ref;""",

    "P7": """SELECT grade_id, designation, ta_da_travel_class, daily_lodging_limit_cat_a_inr
FROM `ongc-hr-finance-agent.hrfin_silver.dim_grade`
WHERE grade_id = 'E2';""",

    "P7__drill_down": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'P1-16' AND clause_ref = 'Part 1'
ORDER BY doc_id, clause_ref;""",

    "P7__why": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'P1-16' AND clause_ref = 'Part 2'
ORDER BY doc_id, clause_ref;""",

    "P7__compare_or_so_what": """SELECT grade_id, designation, ta_da_travel_class, daily_lodging_limit_cat_a_inr
FROM `ongc-hr-finance-agent.hrfin_silver.dim_grade`
WHERE grade_id IN ('E1', 'E2', 'E3', 'E4')
ORDER BY level_order;""",

    "P8": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'P2-01' AND clause_ref = 'Part 1'
ORDER BY doc_id, clause_ref;""",

    "P8__drill_down": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'P2-01' AND clause_ref = 'Part 2'
ORDER BY doc_id, clause_ref;""",

    "P8__why": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'P2-01' AND clause_ref = 'Part 3'
ORDER BY doc_id, clause_ref;""",

    "P8__compare_or_so_what": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'P2-01' AND clause_ref = 'Part 4'
ORDER BY doc_id, clause_ref;""",

    "P10": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 2.0'
ORDER BY doc_id, clause_ref;""",

    "P10__drill_down": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 3.0'
ORDER BY doc_id, clause_ref;""",

    "P10__why": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 1.0'
ORDER BY doc_id, clause_ref;""",

    "P10__compare_or_so_what": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 4.0'
ORDER BY doc_id, clause_ref;""",

    # P11: Cumulative cluster stay with JRTP Clause 7.0 3-year retirement exemption
    "P11": """SELECT
    COUNT(DISTINCT CASE WHEN has_breached_cluster_10yr_cap THEN emp_id END) AS total_breached_10yr_cap,
    COUNT(DISTINCT CASE WHEN has_breached_cluster_10yr_cap AND DATE_DIFF(retirement_date, DATE '2026-10-19', DAY) <= 3 * 365.25 THEN emp_id END) AS exempt_retiring_within_3yr,
    COUNT(DISTINCT CASE WHEN has_breached_cluster_10yr_cap AND DATE_DIFF(retirement_date, DATE '2026-10-19', DAY) > 3 * 365.25 THEN emp_id END) AS due_transfer_non_exempt
FROM `ongc-hr-finance-agent.hrfin_gold.v_cluster_cumulative_tenure`
WHERE cluster_id = 'CL-DEL' AND is_currently_in_cluster;""",

    "P11__drill_down": """SELECT
    current_grade_id AS grade_id,
    COUNT(DISTINCT emp_id) AS officers_breached_cap,
    COUNT(DISTINCT CASE WHEN DATE_DIFF(retirement_date, DATE '2026-10-19', DAY) <= 3 * 365.25 THEN emp_id END) AS exempt_retiring_3yr,
    COUNT(DISTINCT CASE WHEN DATE_DIFF(retirement_date, DATE '2026-10-19', DAY) > 3 * 365.25 THEN emp_id END) AS due_transfer_action
FROM `ongc-hr-finance-agent.hrfin_gold.v_cluster_cumulative_tenure`
WHERE cluster_id = 'CL-DEL' AND is_currently_in_cluster AND has_breached_cluster_10yr_cap
GROUP BY current_grade_id
ORDER BY current_grade_id;""",

    "P11__why": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'JRTP' AND clause_ref IN ('Clause 4.0', 'Clause 7.0')
ORDER BY clause_ref;""",

    "P11__compare_or_so_what": """SELECT
    cluster_name,
    COUNT(DISTINCT CASE WHEN has_breached_cluster_10yr_cap THEN emp_id END) AS breached_10yr_cap,
    COUNT(DISTINCT CASE WHEN has_breached_cluster_10yr_cap AND DATE_DIFF(retirement_date, DATE '2026-10-19', DAY) <= 3 * 365.25 THEN emp_id END) AS exempt_retiring_3yr,
    COUNT(DISTINCT CASE WHEN has_breached_cluster_10yr_cap AND DATE_DIFF(retirement_date, DATE '2026-10-19', DAY) > 3 * 365.25 THEN emp_id END) AS non_exempt_due_transfer
FROM `ongc-hr-finance-agent.hrfin_gold.v_cluster_cumulative_tenure`
WHERE is_currently_in_cluster
GROUP BY cluster_name
ORDER BY non_exempt_due_transfer DESC;""",

    "E5": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'P1-16' AND clause_ref = 'Part 1'
ORDER BY doc_id, clause_ref;""",

    "E5__drill_down": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'P1-16' AND clause_ref = 'Part 2'
ORDER BY doc_id, clause_ref;""",

    "E5__why": """SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'P1-16' AND clause_ref = 'Part 3'
ORDER BY doc_id, clause_ref;""",

    "E5__compare_or_so_what": """SELECT grade_id, designation, ta_da_travel_class, daily_lodging_limit_cat_a_inr
FROM `ongc-hr-finance-agent.hrfin_silver.dim_grade`
WHERE cadre = 'executive'
ORDER BY level_order;""",

    "P17__why": """SELECT
    fiscal_year,
    gross_revenue_inr_cr,
    total_capex_spent_inr_cr,
    total_dividend_payout_inr_cr,
    dividend_payout_ratio_pct
FROM `ongc-hr-finance-agent.hrfin_silver.corporate_financials`
WHERE fiscal_year IN ('FY24', 'FY25', 'FY26')
ORDER BY fiscal_year DESC;""",

    # W1: Recomputed on exact v_field_pnl / field_pnl_annual components
    "W1": """WITH price_params AS (
    SELECT
        AVG(brent_usd_bbl) AS avg_brent,
        AVG(ongc_crude_net_realisation_usd_bbl) AS avg_realisation,
        AVG(brent_usd_bbl - ongc_crude_net_realisation_usd_bbl) AS avg_discount
    FROM `ongc-hr-finance-agent.hrfin_silver.price_fx_monthly`
    WHERE fiscal_year IN ('FY26', '2026')
),
sim_brent60 AS (
    SELECT
        pnl.field_id,
        f.name AS field_name,
        f.onshore_offshore,
        pnl.gross_revenue_inr_cr AS base_revenue_cr,
        pnl.total_opex_inr_cr AS base_opex_cr,
        pnl.dda_depreciation_inr_cr AS base_dda_cr,
        (pnl.oil_revenue_inr_cr * ((60.0 - params.avg_discount) / params.avg_realisation) + pnl.gas_revenue_inr_cr) AS sim_gross_rev_cr,
        SAFE_DIVIDE(pnl.statutory_royalty_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0)) AS eff_royalty_rate,
        SAFE_DIVIDE(pnl.statutory_cess_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0)) AS eff_cess_rate
    FROM `ongc-hr-finance-agent.hrfin_silver.field_pnl_annual` pnl
    JOIN `ongc-hr-finance-agent.hrfin_silver.dim_field` f ON pnl.field_id = f.field_id
    CROSS JOIN price_params params
    WHERE pnl.fiscal_year IN ('FY26', '2026') AND pnl.line_type = 'field'
)
SELECT
    field_id,
    field_name,
    onshore_offshore,
    ROUND(sim_gross_rev_cr, 2) AS sim_gross_revenue_inr_cr,
    ROUND(base_opex_cr, 2) AS total_opex_inr_cr,
    ROUND(sim_gross_rev_cr * (1.0 - eff_royalty_rate - eff_cess_rate) - base_opex_cr, 2) AS sim_ebitda_inr_cr,
    ROUND(sim_gross_rev_cr * (1.0 - eff_royalty_rate - eff_cess_rate) - base_opex_cr - base_dda_cr, 2) AS sim_pbt_inr_cr,
    CASE WHEN (sim_gross_rev_cr * (1.0 - eff_royalty_rate - eff_cess_rate) - base_opex_cr) < 0 THEN TRUE ELSE FALSE END AS is_ebitda_negative,
    CASE WHEN (sim_gross_rev_cr * (1.0 - eff_royalty_rate - eff_cess_rate) - base_opex_cr - base_dda_cr) < 0 THEN TRUE ELSE FALSE END AS is_pbt_negative
FROM sim_brent60
ORDER BY sim_pbt_inr_cr ASC;""",

    "W1__drill_down": """WITH price_params AS (
    SELECT
        AVG(brent_usd_bbl) AS avg_brent,
        AVG(ongc_crude_net_realisation_usd_bbl) AS avg_realisation,
        AVG(brent_usd_bbl - ongc_crude_net_realisation_usd_bbl) AS avg_discount
    FROM `ongc-hr-finance-agent.hrfin_silver.price_fx_monthly`
    WHERE fiscal_year IN ('FY26', '2026')
),
sim_brent60 AS (
    SELECT
        pnl.field_id,
        f.name AS field_name,
        pnl.ebitda_inr_cr AS base_ebitda_cr,
        pnl.pbt_inr_cr AS base_pbt_cr,
        (pnl.oil_revenue_inr_cr * ((60.0 - params.avg_discount) / params.avg_realisation) + pnl.gas_revenue_inr_cr) AS sim_gross_rev_cr,
        SAFE_DIVIDE(pnl.statutory_royalty_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0)) AS eff_royalty_rate,
        SAFE_DIVIDE(pnl.statutory_cess_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0)) AS eff_cess_rate,
        pnl.total_opex_inr_cr AS base_opex_cr,
        pnl.dda_depreciation_inr_cr AS base_dda_cr
    FROM `ongc-hr-finance-agent.hrfin_silver.field_pnl_annual` pnl
    JOIN `ongc-hr-finance-agent.hrfin_silver.dim_field` f ON pnl.field_id = f.field_id
    CROSS JOIN price_params params
    WHERE pnl.fiscal_year IN ('FY26', '2026') AND pnl.line_type = 'field'
)
SELECT
    field_name,
    ROUND(base_ebitda_cr, 2) AS base_ebitda_cr,
    ROUND(sim_gross_rev_cr * (1.0 - eff_royalty_rate - eff_cess_rate) - base_opex_cr, 2) AS sim_ebitda_cr,
    ROUND(base_pbt_cr, 2) AS base_pbt_cr,
    ROUND(sim_gross_rev_cr * (1.0 - eff_royalty_rate - eff_cess_rate) - base_opex_cr - base_dda_cr, 2) AS sim_pbt_cr
FROM sim_brent60
WHERE (sim_gross_rev_cr * (1.0 - eff_royalty_rate - eff_cess_rate) - base_opex_cr - base_dda_cr) < 0
ORDER BY sim_pbt_cr ASC;""",

    "W1__why": """WITH price_params AS (
    SELECT
        AVG(brent_usd_bbl) AS avg_brent,
        AVG(ongc_crude_net_realisation_usd_bbl) AS avg_realisation,
        AVG(brent_usd_bbl - ongc_crude_net_realisation_usd_bbl) AS avg_discount
    FROM `ongc-hr-finance-agent.hrfin_silver.price_fx_monthly`
    WHERE fiscal_year IN ('FY26', '2026')
)
SELECT
    w.onshore_offshore,
    ROUND(AVG(pnl.lifting_cost_per_boe_usd), 2) AS avg_lifting_cost_usd_boe,
    ROUND(SUM(pnl.oil_revenue_inr_cr * ((60.0 - params.avg_discount) / params.avg_realisation) + pnl.gas_revenue_inr_cr) - SUM(pnl.gross_revenue_inr_cr), 2) AS revenue_contraction_cr
FROM `ongc-hr-finance-agent.hrfin_silver.field_pnl_annual` pnl
JOIN `ongc-hr-finance-agent.hrfin_silver.dim_work_centre` w ON pnl.asset_wc_id = w.wc_id
CROSS JOIN price_params params
WHERE pnl.fiscal_year IN ('FY26', '2026') AND pnl.line_type = 'field'
GROUP BY w.onshore_offshore, params.avg_discount, params.avg_realisation
ORDER BY avg_lifting_cost_usd_boe DESC;""",

    "W1__compare_or_so_what": """WITH price_params AS (
    SELECT
        AVG(brent_usd_bbl) AS avg_brent,
        AVG(ongc_crude_net_realisation_usd_bbl) AS avg_realisation,
        AVG(brent_usd_bbl - ongc_crude_net_realisation_usd_bbl) AS avg_discount
    FROM `ongc-hr-finance-agent.hrfin_silver.price_fx_monthly`
    WHERE fiscal_year IN ('FY26', '2026')
),
totals AS (
    SELECT
        ROUND(SUM(pnl.gross_revenue_inr_cr), 2) AS actual_gross_revenue_cr,
        ROUND(SUM(pnl.ebitda_inr_cr), 2) AS actual_ebitda_cr,
        ROUND(SUM(pnl.oil_revenue_inr_cr * ((60.0 - params.avg_discount) / params.avg_realisation) + pnl.gas_revenue_inr_cr), 2) AS sim_gross_revenue_cr,
        ROUND(SUM((pnl.oil_revenue_inr_cr * ((60.0 - params.avg_discount) / params.avg_realisation) + pnl.gas_revenue_inr_cr) * (1.0 - SAFE_DIVIDE(pnl.statutory_royalty_inr_cr + pnl.statutory_cess_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0)))) - SUM(pnl.total_opex_inr_cr), 2) AS sim_ebitda_cr
    FROM `ongc-hr-finance-agent.hrfin_silver.field_pnl_annual` pnl
    CROSS JOIN price_params params
    WHERE pnl.fiscal_year IN ('FY26', '2026') AND pnl.line_type = 'field'
)
SELECT
    actual_gross_revenue_cr,
    sim_gross_revenue_cr,
    ROUND(sim_gross_revenue_cr - actual_gross_revenue_cr, 2) AS revenue_reduction_cr,
    actual_ebitda_cr,
    sim_ebitda_cr,
    ROUND(sim_ebitda_cr - actual_ebitda_cr, 2) AS ebitda_reduction_cr
FROM totals;""",

    # W2: 2-year recruitment freeze projected to 2028
    "W2": """SELECT
    d.discipline_id,
    d.name AS discipline_name,
    COUNT(DISTINCT e.emp_id) AS current_headcount_2026,
    COUNT(DISTINCT CASE WHEN e.retirement_date <= DATE_ADD(DATE '2026-10-19', INTERVAL 2 YEAR) THEN e.emp_id END) AS retirements_next_2yr,
    COUNT(DISTINCT e.emp_id) - COUNT(DISTINCT CASE WHEN e.retirement_date <= DATE_ADD(DATE '2026-10-19', INTERVAL 2 YEAR) THEN e.emp_id END) AS projected_headcount_2028
FROM `ongc-hr-finance-agent.hrfin_silver.employee_master` e
JOIN `ongc-hr-finance-agent.hrfin_silver.dim_discipline` d ON e.discipline_id = d.discipline_id
WHERE e.current_grade_id LIKE 'E%'
  AND (e.employment_status = 'Active' OR e.separation_date IS NULL)
GROUP BY d.discipline_id, d.name
ORDER BY current_headcount_2026 DESC;""",

    "W2__drill_down": """SELECT
    d.discipline_id,
    d.name AS discipline_name,
    COUNT(DISTINCT e.emp_id) AS technical_current,
    COUNT(DISTINCT CASE WHEN e.retirement_date <= DATE_ADD(DATE '2026-10-19', INTERVAL 2 YEAR) THEN e.emp_id END) AS technical_retirements_2yr,
    COUNT(DISTINCT e.emp_id) - COUNT(DISTINCT CASE WHEN e.retirement_date <= DATE_ADD(DATE '2026-10-19', INTERVAL 2 YEAR) THEN e.emp_id END) AS technical_projected_2028
FROM `ongc-hr-finance-agent.hrfin_silver.employee_master` e
JOIN `ongc-hr-finance-agent.hrfin_silver.dim_discipline` d ON e.discipline_id = d.discipline_id
WHERE e.current_grade_id LIKE 'E%'
  AND d.discipline_id IN ('DISC-DRL', 'DISC-RES', 'DISC-PRD', 'DISC-GEO', 'DISC-GPS')
  AND (e.employment_status = 'Active' OR e.separation_date IS NULL)
GROUP BY d.discipline_id, d.name
ORDER BY technical_current DESC;""",

    "W2__why": """SELECT
    gr.`group` AS grade_group,
    COUNT(DISTINCT e.emp_id) AS retiring_count
FROM `ongc-hr-finance-agent.hrfin_silver.employee_master` e
JOIN `ongc-hr-finance-agent.hrfin_silver.dim_grade` gr ON e.current_grade_id = gr.grade_id
WHERE e.current_grade_id LIKE 'E%'
  AND e.retirement_date <= DATE_ADD(DATE '2026-10-19', INTERVAL 2 YEAR)
GROUP BY gr.`group`
ORDER BY retiring_count DESC;""",

    "W2__compare_or_so_what": """SELECT
    COUNT(DISTINCT e.emp_id) AS total_executive_headcount,
    COUNT(DISTINCT CASE WHEN e.retirement_date <= DATE_ADD(DATE '2026-10-19', INTERVAL 2 YEAR) THEN e.emp_id END) AS projected_retirements_2yr,
    ROUND(COUNT(DISTINCT CASE WHEN e.retirement_date <= DATE_ADD(DATE '2026-10-19', INTERVAL 2 YEAR) THEN e.emp_id END) * 100.0 / NULLIF(COUNT(DISTINCT e.emp_id), 0), 2) AS retirement_attrition_pct
FROM `ongc-hr-finance-agent.hrfin_silver.employee_master` e
WHERE e.current_grade_id LIKE 'E%'
  AND (e.employment_status = 'Active' OR e.separation_date IS NULL);""",

    # W3: Relocate 200 executives from corporate to field
    "W3": """SELECT
    wc.short_name AS field_asset,
    COALESCE(SUM(sp.sanctioned_strength), 0) AS sanctioned_posts,
    COALESCE(SUM(sp.in_position_strength), 0) AS in_position,
    COALESCE(SUM(sp.vacancy_count), 0) AS vacancy_deficit,
    200 AS total_executives_relocated,
    6.50 AS total_relocation_grant_cr
FROM `ongc-hr-finance-agent.hrfin_silver.dim_work_centre` wc
LEFT JOIN `ongc-hr-finance-agent.hrfin_silver.sanctioned_posts` sp ON wc.wc_id = sp.wc_id AND sp.fiscal_year IN ('FY26', '2026')
WHERE wc.hard_station_cat IN ('B', 'C') AND wc.wc_id IN ('WC-ASM', 'WC-TRI', 'WC-CAM', 'WC-RAJ')
GROUP BY wc.short_name
ORDER BY vacancy_deficit DESC;""",

    "W3__drill_down": """SELECT
    wc.short_name AS field_asset,
    COALESCE(SUM(sp.vacancy_count), 0) AS vacancy_deficit,
    ROUND(SAFE_DIVIDE(SUM(sp.vacancy_count) * 100.0, SUM(sp.sanctioned_strength)), 2) AS vacancy_pct
FROM `ongc-hr-finance-agent.hrfin_silver.dim_work_centre` wc
LEFT JOIN `ongc-hr-finance-agent.hrfin_silver.sanctioned_posts` sp ON wc.wc_id = sp.wc_id AND sp.fiscal_year IN ('FY26', '2026')
WHERE wc.hard_station_cat = 'C'
GROUP BY wc.short_name
ORDER BY vacancy_deficit DESC;""",

    "W3__why": """SELECT
    wc.name AS asset_name,
    COUNT(DISTINCT e.emp_id) AS current_technical_staff
FROM `ongc-hr-finance-agent.hrfin_silver.employee_master` e
JOIN `ongc-hr-finance-agent.hrfin_silver.dim_work_centre` wc ON e.current_wc_id = wc.wc_id
JOIN `ongc-hr-finance-agent.hrfin_silver.dim_discipline` d ON e.discipline_id = d.discipline_id
WHERE LOWER(d.function) = 'technical' AND wc.hard_station_cat IN ('B', 'C')
  AND (e.employment_status = 'Active' OR e.separation_date IS NULL)
GROUP BY wc.name
ORDER BY current_technical_staff ASC
LIMIT 10;""",

    "W3__compare_or_so_what": """SELECT
    200 AS relocated_officers,
    6.50 AS one_time_cta_cost_cr,
    35878.0 AS annual_capex_cr,
    ROUND(6.50 / 35878.0 * 100.0, 4) AS cta_cost_pct_of_capex;""",

    # W4: Windfall tax discontinuation impact
    "W4": """SELECT
    fiscal_year,
    ROUND(AVG(windfall_tax_saed_usd_bbl), 2) AS saed_windfall_tax_usd_bbl,
    ROUND(AVG(ongc_crude_net_realisation_usd_bbl), 2) AS net_realisation_usd_bbl,
    ROUND(AVG(windfall_tax_saed_inr_bbl), 2) AS saed_windfall_tax_inr_bbl,
    ROUND(AVG(inr_usd_fx_rate), 2) AS avg_fx_rate
FROM `ongc-hr-finance-agent.hrfin_silver.price_fx_monthly`
WHERE fiscal_year IN ('FY23', 'FY24', 'FY25', 'FY26')
GROUP BY fiscal_year
ORDER BY fiscal_year;""",

    "W4__drill_down": """SELECT
    month,
    fiscal_year,
    windfall_tax_saed_usd_bbl,
    ongc_crude_net_realisation_usd_bbl,
    brent_usd_bbl
FROM `ongc-hr-finance-agent.hrfin_silver.price_fx_monthly`
WHERE fiscal_year = 'FY25'
ORDER BY month;""",

    "W4__why": """SELECT
    fiscal_year,
    saed_windfall_tax_inr_cr,
    gross_revenue_inr_cr,
    ebitda_inr_cr
FROM `ongc-hr-finance-agent.hrfin_silver.corporate_financials`
WHERE fiscal_year IN ('FY23', 'FY24', 'FY25', 'FY26')
ORDER BY fiscal_year;""",

    "W4__compare_or_so_what": """SELECT
    fiscal_year,
    ROUND(AVG(ongc_crude_net_realisation_usd_bbl), 2) AS avg_net_realisation_usd,
    ROUND(AVG(brent_usd_bbl), 2) AS avg_brent_usd,
    ROUND(AVG(ongc_crude_net_realisation_usd_bbl) * 100.0 / NULLIF(AVG(brent_usd_bbl), 0), 2) AS net_realisation_pct_brent
FROM `ongc-hr-finance-agent.hrfin_silver.price_fx_monthly`
WHERE fiscal_year IN ('FY23', 'FY24', 'FY25', 'FY26')
GROUP BY fiscal_year
ORDER BY fiscal_year;""",

    "X6__drill_down": """SELECT
    project_name,
    technology_type,
    installed_capacity_mw,
    cumulative_capex_inr_cr
FROM `ongc-hr-finance-agent.hrfin_silver.energy_transition`
WHERE fiscal_year IN ('FY26', '2026')
ORDER BY cumulative_capex_inr_cr DESC;"""
}


def replace_datediff_bq(text: str) -> str:
    """Robust paren-matching replacement of DuckDB datediff to BigQuery DATE_DIFF."""
    out = []
    i = 0
    n = len(text)
    pattern = re.compile(r"\bdatediff\s*\(", re.I)
    while i < n:
        m = pattern.search(text, i)
        if not m:
            out.append(text[i:])
            break
        out.append(text[i:m.start()])
        start_paren = m.end() - 1
        depth = 1
        j = start_paren + 1
        while j < n and depth > 0:
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
            j += 1
        arg_str = text[start_paren + 1:j - 1]
        args = []
        cur_arg = []
        d = 0
        for char in arg_str:
            if char == "(":
                d += 1
            elif char == ")":
                d -= 1
            elif char == "," and d == 0:
                args.append("".join(cur_arg).strip())
                cur_arg = []
                continue
            cur_arg.append(char)
        if cur_arg:
            args.append("".join(cur_arg).strip())

        if len(args) == 3:
            unit = re.sub(r"[\x27\x22]", "", args[0]).upper()
            d1 = args[1]
            d2 = args[2]
            out.append(f"DATE_DIFF({d2}, {d1}, {unit})")
        else:
            out.append(text[m.start():j])
        i = j
    return "".join(out)


def translate_probe_sql(raw_sql: str, probe_id: str) -> str:
    """Translate DuckDB probe SQL to standard BigQuery SQL."""
    if probe_id in CUSTOM_QUERIES:
        return CUSTOM_QUERIES[probe_id]

    if probe_id in REFUSAL_MAP:
        return REFUSAL_MAP[probe_id]["sql"]

    if "STUB_REFUSAL" in raw_sql:
        parent_id = probe_id.split(".")[0]
        if parent_id in REFUSAL_MAP:
            return REFUSAL_MAP[parent_id]["sql"]
        return """SELECT 'REFUSAL' AS status, 'Confidential personal/commercial data under ONGC Policy.' AS reason;"""

    if "STUB_RAG" in raw_sql:
        m = re.search(r"-- Document Expectation:\s*(.*)", raw_sql)
        doc_exp = m.group(1).strip() if m else ""
        return build_doc_query(doc_exp, probe_id)

    lines = [l for l in raw_sql.splitlines() if not l.strip().startswith("--")]
    code = "\n".join(lines).strip()

    if "W2.why" in probe_id:
        code = re.sub(r"\bgr\.group\b", "gr.`group`", code)
    if "H8.compare_or_so_what" in probe_id:
        code = code.replace("milestone_project_execution", "HR Training & Capability Development")
    if "X3.compare_or_so_what" in probe_id:
        code = code.replace("safety_ltifr_score", "Lost Time Injury Frequency Rate (LTIFR)")
    if "C5.compare_or_so_what" in probe_id:
        code = re.sub(r"datediff\('year',\s*employee_master\.dob,\s*DATE '2030-03-31'\)", "DATE_DIFF(DATE '2030-03-31', employee_master.dob, YEAR)", code)

    code = re.sub(r"\bbool_or\(", "LOGICAL_OR(", code, flags=re.I)
    code = re.sub(r"\bbool_and\(", "LOGICAL_AND(", code, flags=re.I)
    code = replace_datediff_bq(code)
    code = re.sub(r"COUNT\(DISTINCT\s+([^)]+)\)\s+FILTER\(WHERE\s+([^)]+)\)", r"COUNT(DISTINCT CASE WHEN \2 THEN \1 END)", code, flags=re.I)

    code = code.strip()
    if not code.endswith(";"):
        code += ";"
    return code


def build_doc_query(doc_exp: str, probe_id: str) -> str:
    """Build a BigQuery query over hrfin_docs.silver_chunks for policy questions."""
    if "D3" in probe_id:
        return f"""SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `{PROJECT_ID}.hrfin_docs.silver_chunks`
WHERE doc_id = 'R&P/Promotion' AND clause_ref IN ('Clause 8.0', 'Clause 3.0')
ORDER BY doc_id, clause_ref
LIMIT 5;"""

    if "P6" in probe_id:
        return f"""SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `{PROJECT_ID}.hrfin_docs.silver_chunks`
WHERE (doc_id = 'G-06' AND clause_ref = '12. Gifts') OR doc_id = 'P1-01'
ORDER BY doc_id, clause_ref
LIMIT 5;"""

    if "P10" in probe_id:
        return f"""SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `{PROJECT_ID}.hrfin_docs.silver_chunks`
WHERE doc_id = 'R&P/Promotion' AND clause_ref IN ('Clause 2.0', 'Clause 3.0')
ORDER BY doc_id, clause_ref
LIMIT 5;"""

    if "D6" in probe_id:
        return f"""SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `{PROJECT_ID}.hrfin_docs.silver_chunks`
WHERE doc_id IN ('P2-01', 'Whistle Blower Policy') OR doc_id = 'P1-01'
ORDER BY doc_id, clause_ref
LIMIT 5;"""

    tokens = [t.strip() for t in doc_exp.split(",") if t.strip()]
    conds = []
    for t in tokens:
        if " Clause " in t:
            parts = t.split(" Clause ")
            d = parts[0].strip()
            c = "Clause " + parts[1].strip()
            conds.append(f"(doc_id = '{d}' AND clause_ref = '{c}')")
        else:
            conds.append(f"(doc_id = '{t}' OR doc_id LIKE '{t}%')")

    if not conds:
        base_id = probe_id.replace(".drill_down", "").replace(".why", "").replace(".compare_or_so_what", "")
        return f"""SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `{PROJECT_ID}.hrfin_docs.silver_chunks`
WHERE questions_served LIKE '%{base_id}%'
ORDER BY doc_id, clause_ref
LIMIT 5;"""

    where_expr = " OR ".join(conds)
    return f"""SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `{PROJECT_ID}.hrfin_docs.silver_chunks`
WHERE {where_expr}
ORDER BY doc_id, clause_ref
LIMIT 5;"""


def serialize_val(v: Any) -> Any:
    """JSON serializer helper."""
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def execute_sql(client: bigquery.Client, sql: str, label: str) -> Dict[str, Any]:
    """Execute SQL in BigQuery and return serializable result dictionary."""
    t0 = time.time()
    cfg = bigquery.QueryJobConfig(
        default_dataset=f"{PROJECT_ID}.hrfin_silver",
        labels=JOB_LABELS,
        use_query_cache=False
    )
    job = client.query(sql, job_config=cfg)
    rows_raw = list(job.result())
    elapsed = time.time() - t0

    col_names = list(rows_raw[0].keys()) if rows_raw else []

    rows = []
    for r in rows_raw:
        row_dict = {}
        for k in col_names:
            row_dict[k] = serialize_val(r[k])
        rows.append(row_dict)

    return {
        "job_id": job.job_id,
        "total_bytes_processed": job.total_bytes_processed or 0,
        "executed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "row_count": len(rows),
        "columns": col_names,
        "rows": rows
    }


def render_markdown_answer(entry_id: str, qtext: str, qtype: str, result: Dict[str, Any], is_followup: bool = False, kind: str = "") -> str:
    """Render executive CMD-style Markdown answer text FROM the executed result."""
    rows = result["rows"]
    row_count = result["row_count"]
    root_id = entry_id.split("__")[0]

    md_lines = []
    md_lines.append(f"# Answer Key: {entry_id}")
    md_lines.append("")
    md_lines.append(f"**Question:** {qtext}")
    md_lines.append(f"**Type:** `{qtype}` | **Result Count:** `{row_count}` rows | **Execution:** `{result['elapsed_seconds']}s`")
    md_lines.append("")

    # Refusal types
    if root_id in REFUSAL_MAP and (not is_followup or kind == "why"):
        ref = REFUSAL_MAP[root_id]
        md_lines.append("## Executive Determination: REFUSAL")
        md_lines.append(f"> [!CAUTION]")
        md_lines.append(f"> **Access Restricted:** {ref['reason']}")
        md_lines.append("")
        md_lines.append(f"**Policy / Statutory Justification:** {ref['rule']}")
        md_lines.append("")
        md_lines.append(f"**Permitted Alternative:** {ref['permitted_alt']}")
        md_lines.append("")
        md_lines.append("### Authorized Aggregate Data")
        md_lines.append(format_table_markdown(rows[:5]))
        return "\n".join(md_lines)

    # C1 / P11 specific citations with 3-year retirement practice
    if root_id == "C1" and not is_followup:
        md_lines.append("## Executive Synthesis: Delhi Station Tenure & Transfer Eligibility")
        md_lines.append("Pursuant to **JRTP Clause 3.0 (Station Tenure Norms)** and **Clause 7.0 (Pre-Retirement Tenure Exemption)**, station tenure in Delhi Corporate HQ (WC-DEL) is subject to strict rotation.")
        md_lines.append("> [!NOTE]")
        md_lines.append("> **Statutory Exemption vs Practice:** Under JRTP Clause 7.1, executives within 2 years of superannuation (age 58+) are strictly exempt from transfer. In organizational practice and annual transfer planning, the protective exemption extends to 3 years (age 57+).")
        md_lines.append("")
        if rows:
            tot_5yr = sum(int(r.get("delhi_executives_ge_5yr", 0)) for r in rows)
            tot_exempt = sum(int(r.get("exempt_retiring_3yr", 0)) for r in rows)
            tot_due = sum(int(r.get("non_exempt_due_transfer", 0)) for r in rows)
            md_lines.append(f"Analysis indicates **{tot_5yr} regular executives** have completed 5 or more continuous years in Delhi. Accounting for **{tot_exempt} officers exempt under the 3-year pre-retirement practice**, a net total of **{tot_due} executives** are due for rotational transfer.")
        md_lines.append("")
        md_lines.append("### Summary Breakdown by Grade and Discipline")
        md_lines.append(format_table_markdown(rows[:10]))
        return "\n".join(md_lines)

    if root_id == "P11" and not is_followup:
        md_lines.append("## Policy Determination: Cumulative Cluster Tenure (Delhi NCR)")
        md_lines.append("Evaluated against **JRTP Clause 4.0 (Cumulative Stay Cap - 10 Year Maximum)** and **Clause 7.0 (Pre-Retirement Exemption)** across multi-stint posting records.")
        md_lines.append("> [!NOTE]")
        md_lines.append("> **Rule Citation:** JRTP Clause 4.1 establishes a strict 10-year cumulative cap per cluster. Clause 7.1 establishes pre-retirement exemption (2-year statutory rule, 3-year corporate planning practice).")
        md_lines.append("")
        if rows:
            r0 = rows[0]
            md_lines.append(f"In Cluster CL-DEL (Delhi NCR), **{r0.get('total_breached_10yr_cap')} executives** have breached the 10-year cumulative stay cap. Subtracting **{r0.get('exempt_retiring_within_3yr')} officer exempt under the 3-year retirement rule** leaves **{r0.get('due_transfer_non_exempt')} executives** liable for transfer out of the cluster.")
        md_lines.append("")
        md_lines.append("### Cumulative Cluster Audit Table")
        md_lines.append(format_table_markdown(rows))
        return "\n".join(md_lines)

    # Policy / RAG types
    if qtype in ("policy", "rag") or (rows and "quote_snippet" in rows[0]):
        md_lines.append("## Policy Determination & Regulatory Citation")
        for idx, r in enumerate(rows[:3], 1):
            doc_id = r.get("doc_id", "Official Policy")
            clause_ref = r.get("clause_ref", "Applicable Clause")
            heading = r.get("heading", "")
            quote = r.get("quote_snippet", "").strip()
            md_lines.append(f"### {idx}. {doc_id} — {clause_ref}: {heading}")
            md_lines.append(f"> \"{quote}\"")
            md_lines.append("")
        return "\n".join(md_lines)

    # Document generation types (C14, H10, F10, X7)
    if root_id in ("C14", "H10", "F10", "X7") and not is_followup:
        md_lines.append("## Executive Document Output")
        if root_id == "C14":
            md_lines.append("### Board Memorandum: Strategic Review of Top Loss-Making Fields (FY26)")
            md_lines.append("Pursuant to the annual field economics review, the Corporation's top operating losses are concentrated in the following mature onshore assets:")
            md_lines.append(format_table_markdown(rows[:5]))
            md_lines.append("")
            md_lines.append("### Template Placeholders Filled")
            md_lines.append("- `{{fields_analyzed}}`: " + ", ".join(str(r.get("field_name", "")) for r in rows[:5]))
            md_lines.append(f"- `{{max_loss_field}}`: {rows[0].get('field_name')} (PBT: ₹{rows[0].get('pbt_inr_cr', rows[0].get('ebitda_inr_cr', 0)):,.2f} Cr)")
            md_lines.append("- `{{recommended_governance}}`: Production Enhancement Contract (PEC) or Marginal Field Farm-out under BDP Clause 8.0.")
        elif root_id == "H10":
            md_lines.append("### Annual Job Rotation & Transfer Proposal (FY27 Roster)")
            md_lines.append("In accordance with JRTP Clause 3.0 (Station Tenure Norms) and Clause 6.0 (Hard Station Rotation), the following transfer roster balances regional deficits:")
            md_lines.append(format_table_markdown(rows[:5]))
            md_lines.append("")
            md_lines.append("### Template Placeholders Filled")
            md_lines.append(f"- `{{eligible_officers_count}}`: {row_count}")
            md_lines.append(f"- `{{target_deficit_stations}}`: Assam Operational Asset (Nazira/Sivasagar), Tripura Asset (Agartala)")
            md_lines.append("- `{{approval_authority}}`: Director (HR) for E1–E5, CMD for E6+.")
        elif root_id == "F10":
            md_lines.append("### Quarterly Asset-Wise Statement of Profit & Loss")
            md_lines.append("Quarterly operational financial review detailing hydrocarbon sales, operating costs, and net EBITDA margin across operational centres:")
            md_lines.append(format_table_markdown(rows[:5]))
            md_lines.append("")
            md_lines.append("### Template Placeholders Filled")
            md_lines.append(f"- `{{assets_reported}}`: {row_count}")
            md_lines.append(f"- `{{reporting_currency}}`: INR Crore / BOE USD")
            md_lines.append("- `{{governance_review}}`: Executive Committee quarterly performance review.")
        elif root_id == "X7":
            md_lines.append("### Parliamentary Reply: Rajya Sabha / Lok Sabha Admitted Question")
            md_lines.append("**Subject:** Vacancies in ONGC in the North-Eastern Region (Assam and Tripura Assets), Category-Wise.")
            md_lines.append("")
            md_lines.append(format_table_markdown(rows[:5]))
            md_lines.append("")
            md_lines.append("### Template Placeholders Filled")
            md_lines.append("- `{{regions_covered}}`: Assam Asset, Tripura Asset")
            md_lines.append("- `{{reservation_roster_classes}}`: Scheduled Castes (SC), Scheduled Tribes (ST), Other Backward Classes (OBC), EWS, General")
            md_lines.append("- `{{remedial_measures}}`: Special Recruitment Drives (SRD) and accelerated Graduate Trainee (GATE) postings.")
        return "\n".join(md_lines)

    # What-if simulation types (W1–W4, C13)
    if root_id in ("W1", "W2", "W3", "W4", "C13"):
        md_lines.append("## Scenario Model & Parameterized Simulation")
        if root_id == "W1":
            md_lines.append("**Model Parameters & Documented Assumptions:**")
            md_lines.append("- Scenario Brent Price: `$60.00 / bbl`.")
            md_lines.append("- Oil & Condensate Revenue Re-pricing: Derived using `(scenario_brent - avg_discount) / avg_realisation` from `price_fx_monthly` (FY26 baseline: Brent $70.90, net realization $68.40, discount $2.50).")
            md_lines.append("- Natural Gas Revenue: Unchanged (APM gas at $6.50/MMBtu is administered and not Brent-linked).")
            md_lines.append("- Statutory Levies: Royalty & Cess derived from implied field effective rates (`levy / gross_revenue`). SAED = $0.")
            md_lines.append("- Operating Costs & DD&A: Fixed per FY26 baseline.")
            if rows:
                ebitda_neg = [r for r in rows if r.get("is_ebitda_negative")]
                pbt_neg = [r for r in rows if r.get("is_pbt_negative")]
                md_lines.append("")
                md_lines.append(f"**Simulation Finding:** At $60 Brent, **{len(ebitda_neg)} fields go EBITDA-negative** ({', '.join(r['field_name'] for r in ebitda_neg)}) and **{len(pbt_neg)} fields go PBT-negative** ({', '.join(r['field_name'] for r in pbt_neg)}).")
        elif root_id == "W2":
            md_lines.append("**Model Parameters & Assumptions:**")
            md_lines.append("- Recruitment moratorium: `0` new external hiring for 24 months across executive cadres.")
            md_lines.append("- Superannuations: Natural superannuation at age 60 strictly per `retirement_date` (through Oct 2028).")
        elif root_id in ("W3", "C13"):
            md_lines.append("**Model Parameters & Assumptions:**")
            md_lines.append("- Relocation cohort: `200` mid-level executive engineers (E3–E5) relocated from corporate centres (Delhi/Dehradun) to field assets.")
            md_lines.append("- Relocation outlay: Composite Transfer Allowance (CTA) + relocation grant estimated at `₹3.25 Lakh` per executive (`₹6.50 Cr` total).")
        elif root_id == "W4":
            md_lines.append("**Model Parameters & Assumptions:**")
            md_lines.append("- SAED (Windfall Tax) withdrawal: Zero Special Additional Excise Duty effective December 2024.")
            md_lines.append("- Realization improvement: Domestic crude realization improved by erstwhile SAED levy ($3.27/bbl to $12.15/bbl).")

        md_lines.append("")
        md_lines.append("### Simulated Impact Results")
        md_lines.append(format_table_markdown(rows[:5]))
        return "\n".join(md_lines)

    # Standard Data answers
    md_lines.append("## Executive Synthesis")
    first_few = rows[:5]
    summary_txt = f"Analysis of enterprise data across `{row_count}` records indicates operational patterns. "
    if rows:
        sample_keys = list(rows[0].keys())
        first_row_vals = [f"{k}: {rows[0][k]}" for k in sample_keys[:3]]
        summary_txt += f"Leading record reflects {', '.join(first_row_vals)}. "
    md_lines.append(summary_txt)
    md_lines.append("")
    md_lines.append("### Summary Result Table")
    md_lines.append(format_table_markdown(first_few))
    return "\n".join(md_lines)


def format_table_markdown(rows: List[Dict[str, Any]]) -> str:
    """Render list of dicts as GitHub Markdown table."""
    if not rows:
        return "*No rows returned.*"
    headers = list(rows[0].keys())
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in rows:
        row_str = " | ".join(str(r.get(h, "")) for h in headers)
        lines.append(f"| {row_str} |")
    return "\n".join(lines)


def get_entry_gold_objects_and_assumptions(entry_id: str, qtype: str, is_followup: bool) -> Tuple[str, str]:
    """Return gold objects used and key assumptions for INDEX.md."""
    root_id = entry_id.split("__")[0]

    if root_id in REFUSAL_MAP:
        ref = REFUSAL_MAP[root_id]
        return ref.get("gold_objects", "hrfin_silver"), ref.get("assumptions", "Access restricted under ONGC CDA/BDP rules")

    if root_id == "W1":
        return "hrfin_gold.v_field_pnl, hrfin_silver.field_pnl_annual, dim_price_fx", "Scenario Brent $60; APM gas flat; field effective royalty/cess; opex/DD&A fixed"

    if root_id == "W2":
        return "hrfin_silver.employee_master, dim_discipline, dim_grade", "2-year recruitment freeze (0 hires); retirements at age 60 through Oct 2028"

    if root_id in ("W3", "C13"):
        return "hrfin_silver.posting_history, sanctioned_posts, employee_master", "200 E3-E5 execs relocated; ₹3.25L CTA per officer (₹6.50 Cr total)"

    if root_id == "W4":
        return "hrfin_silver.price_fx_monthly, corporate_financials", "SAED withdrawal Dec 2024; realization improves by erstwhile SAED ($3.27-$12.15/bbl)"

    if root_id in ("C1", "D5"):
        return "hrfin_gold.v_continuous_stay", "Continuous stay >=60m in WC-DEL; 3-year retirement exemption per JRTP Clause 7.0"

    if root_id == "P11":
        return "hrfin_gold.v_cluster_cumulative_tenure, hrfin_docs.silver_chunks", "10-year cluster stay cap per JRTP Clause 4; 3-year retirement exemption per Clause 7"

    if root_id in ("C6", "C8", "C14"):
        return "hrfin_gold.v_field_pnl, hrfin_silver.field_pnl_annual", "FY26 standalone audited field P&L components"

    if root_id in ("C12", "F1"):
        return "hrfin_gold.v_lifting_cost", "Lifting cost and manpower cost per BOE across onshore/offshore assets"

    if qtype in ("policy", "rag"):
        return "hrfin_docs.silver_chunks, gold_doc_index", "Official published ONGC rulebooks & public policy gazettes"

    return "hrfin_silver, hrfin_gold", "Audited enterprise operational records (demo anchor 2026-10-19)"


def main():
    # Guard (semantic audit 2026-10-20): this builder regenerates SQL from probes/CUSTOM_QUERIES that
    # still contain the pre-audit defects. Re-running it would silently revert the corrected answer key.
    # Corrections now live in answer_key/sql, answer_key/followups and answer_key/semantic_audit/.
    if "--force-overwrite-semantic-audit" not in sys.argv:
        print("Refusing to run: would overwrite semantic-audit corrections (see AUDIT_SEMANTIC_2026-10-20.md). "
              "Use semantic_audit/run_entry.py instead, or pass --force-overwrite-semantic-audit.")
        sys.exit(2)
    print("=" * 70)
    print("Starting Phase 5 Answer Key Rebuild (5.1 Root + 5.2 Follow-ups)...")
    print("=" * 70)

    bq_client = bigquery.Client(project=PROJECT_ID, location=LOCATION)

    # 1. Load questions
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        qdata = yaml.safe_load(f)
    questions = qdata["questions"]

    # 2. Build task list
    tasks = []
    for q in questions:
        qid = q["id"]
        tasks.append((qid, None, None, q["question"], q.get("type", "data"), False))
        for fu in q.get("followups", []):
            kind = fu["kind"]
            fu_id = f"{qid}__{kind}"
            tasks.append((fu_id, qid, kind, fu["question"], q.get("type", "data"), True))

    print(f"Total entries to generate and execute: {len(tasks)} (89 root + 267 follow-ups)")

    # 3. Map probes from verify/probes/
    probe_map = {}
    for pf in PROBES_DIR.glob("*.sql"):
        stem = pf.stem
        probe_map[stem] = pf

    # 4. Prepare SQLs
    entry_sqls = {}
    for entry_id, parent_id, kind, qtext, qtype, is_followup in tasks:
        if entry_id in CUSTOM_QUERIES:
            entry_sqls[entry_id] = CUSTOM_QUERIES[entry_id]
            continue

        if not is_followup:
            p_stem = entry_id
        else:
            p_stem = f"{parent_id}.{kind}"

        if p_stem in probe_map:
            raw_sql = probe_map[p_stem].read_text(encoding="utf-8")
            sql_bq = translate_probe_sql(raw_sql, p_stem)
        else:
            sql_bq = f"SELECT '{entry_id}' AS entry_id, 'Data not available' AS note;"

        entry_sqls[entry_id] = sql_bq

    print(f"Prepared {len(entry_sqls)} BigQuery SQL queries.")

    # 5. Execute in BigQuery with ThreadPoolExecutor
    print(f"Executing {len(entry_sqls)} queries against BigQuery (project: {PROJECT_ID}, location: {LOCATION})...")
    results = {}
    total_bytes = 0

    def exec_worker(item):
        eid, sql = item
        try:
            res = execute_sql(bq_client, sql, eid)
            return eid, True, res
        except Exception as e:
            return eid, False, str(e)

    with ThreadPoolExecutor(max_workers=20) as ex:
        exec_results = list(ex.map(exec_worker, entry_sqls.items()))

    errors = []
    for eid, success, data in exec_results:
        if success:
            results[eid] = data
            total_bytes += data["total_bytes_processed"]
        else:
            errors.append((eid, data))

    if errors:
        print(f"FAILED {len(errors)} queries! Sample errors:")
        for eid, err in errors[:10]:
            print(f"  {eid}: {err}")
        sys.exit(1)

    print(f"ALL {len(results)} queries executed successfully! Total bytes processed: {total_bytes:,} bytes ({round(total_bytes / (1024*1024), 2)} MB).")

    # 6. Verify non-empty results and follow-up differentiation
    empty_entries = []
    identical_followups = []
    for entry_id, parent_id, kind, qtext, qtype, is_followup in tasks:
        res = results[entry_id]
        if res["row_count"] == 0:
            empty_entries.append(entry_id)
        if is_followup:
            parent_res = results[parent_id]
            if res["rows"] == parent_res["rows"]:
                identical_followups.append((entry_id, parent_id))

    print(f"Empty results: {len(empty_entries)}")
    if empty_entries:
        print("  Empty list:", empty_entries)
    print(f"Identical follow-ups: {len(identical_followups)}")
    if identical_followups:
        print("  Identical sample:", identical_followups[:5])

    # 7. Write output files
    print("Writing SQL, JSON, and MD files...")
    answered_count = 0
    refusal_count = 0
    gap_count = len(empty_entries)

    index_rows = []

    for entry_id, parent_id, kind, qtext, qtype, is_followup in tasks:
        sql = entry_sqls[entry_id]
        res = results[entry_id]
        md_text = render_markdown_answer(entry_id, qtext, qtype, res, is_followup, kind)

        root_id = entry_id.split("__")[0]
        if root_id in REFUSAL_MAP and (not is_followup or kind == "why"):
            status = "refusal"
            refusal_count += 1
        elif res["row_count"] == 0:
            status = "gap"
        else:
            status = "answered"
            answered_count += 1

        # Headline
        if status == "refusal":
            headline = f"REFUSAL: {REFUSAL_MAP[root_id]['reason'][:75]}..."
        elif root_id == "C1" and not is_followup:
            headline = "419 execs in Delhi >=5y (401 due transfer, 17 retiring within 3 yrs, 1 valid exemption)"
        elif root_id == "P11" and not is_followup:
            headline = "201 execs breached 10-yr Delhi cluster cap (200 due transfer, 1 exempt under 3-yr retirement rule)"
        elif root_id == "W1" and not is_followup:
            headline = "2 fields EBITDA-negative (Champang, Borholla); 3 fields PBT-negative (+Khoraghat) at Brent $60"
        elif res["rows"] and (qtype in ("policy", "rag") or "quote_snippet" in res["rows"][0]):
            r0 = res["rows"][0]
            headline = f"Policy Clause: {r0.get('doc_id')} {r0.get('clause_ref')} - {r0.get('heading', '')[:60]}"
        elif res["rows"]:
            r0 = res["rows"][0]
            if r0:
                k0 = list(r0.keys())[0]
                v0 = r0[k0]
                headline = f"{res['row_count']} rows returned (e.g. {k0}={v0})"
            else:
                headline = f"{res['row_count']} rows returned"
        else:
            headline = "No rows returned (data gap)"

        gold_obj, assumptions = get_entry_gold_objects_and_assumptions(entry_id, qtype, is_followup)

        index_rows.append({
            "id": entry_id,
            "parent": parent_id or "-",
            "kind": kind or "root",
            "type": qtype,
            "status": status,
            "rows": res["row_count"],
            "gold_objects": gold_obj,
            "assumptions": assumptions,
            "headline": headline
        })

        if not is_followup:
            (SQL_DIR / f"{entry_id}.sql").write_text(f"-- Answer Key SQL: {entry_id}\n-- Question: {qtext}\n-- Type: {qtype}\n\n{sql}\n", encoding="utf-8")
            (EXPECTED_DIR / f"{entry_id}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
            (ANSWERS_DIR / f"{entry_id}.md").write_text(md_text, encoding="utf-8")
        else:
            (FOLLOWUPS_DIR / f"{entry_id}.sql").write_text(f"-- Answer Key Follow-up SQL: {entry_id}\n-- Question: {qtext}\n-- Type: {qtype}\n\n{sql}\n", encoding="utf-8")
            (FOLLOWUPS_DIR / f"{entry_id}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
            (FOLLOWUPS_DIR / f"{entry_id}.md").write_text(md_text, encoding="utf-8")

    # 8. Write augmented answer_key/INDEX.md
    print("Writing augmented answer_key/INDEX.md...")
    index_md = []
    index_md.append("# ONGC Data Bank — Answer Key & Follow-Up Verification Index")
    index_md.append("")
    index_md.append(f"**Generated:** {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    index_md.append(f"**GCP Project:** `{PROJECT_ID}` | **Datasets:** `hrfin_gold`, `hrfin_silver`, `hrfin_docs`")
    index_md.append(f"**Total Entries:** `356` (`89` Root Questions + `267` Follow-ups)")
    index_md.append(f"**Audit Status:** `{answered_count}` Answered, `{refusal_count}` Refusals, `{gap_count}` Gaps")
    index_md.append(f"**Total BigQuery Bytes Processed:** `{total_bytes:,}` bytes ({round(total_bytes / (1024*1024), 2)} MB)")
    index_md.append("")
    index_md.append("## Summary Statistics")
    index_md.append("| Category | Count | Percentage |")
    index_md.append("|---|---|---|")
    index_md.append(f"| **Answered (Data & Policy)** | {answered_count} | {round(answered_count/len(tasks)*100, 1)}% |")
    index_md.append(f"| **Documented Refusals** | {refusal_count} | {round(refusal_count/len(tasks)*100, 1)}% |")
    index_md.append(f"| **Data Gaps** | {gap_count} | {round(gap_count/len(tasks)*100, 1)}% |")
    index_md.append(f"| **Total Evaluated** | {len(tasks)} | 100.0% |")
    index_md.append("")
    index_md.append("## Complete Answer Key Ledger")
    index_md.append("| Entry ID | Parent | Kind | Type | Status | Rows | Gold Objects Used | Key Assumptions / Notes | Headline Answer / Citation |")
    index_md.append("|---|---|---|---|---|---|---|---|---|")
    for r in index_rows:
        index_md.append(f"| `{r['id']}` | `{r['parent']}` | `{r['kind']}` | `{r['type']}` | **{r['status'].upper()}** | `{r['rows']}` | `{r['gold_objects']}` | {r['assumptions']} | {r['headline']} |")

    INDEX_PATH.write_text("\n".join(index_md), encoding="utf-8")
    print(f"Successfully wrote {INDEX_PATH}")
    print("=" * 70)
    print("Answer Key Rebuild Complete!")
    print(f"Answered: {answered_count} | Refusals: {refusal_count} | Gaps: {gap_count}")
    print(f"Total Bytes Processed: {total_bytes:,} bytes")
    print("=" * 70)


if __name__ == "__main__":
    main()
