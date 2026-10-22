"""Semantic Layer and SQL Safety Engine for Yukti AI.
Contains enterprise table schemas, metric definitions, join paths,
and enforces query-craft rules and SQL safety checks.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from google.cloud import bigquery

from app.semantic.normalize import normalize_categorical_filters
from app.config import (
    ALLOWED_DATASETS,
    BQ_LOCATION,
    GCP_PROJECT,
    JOB_LABELS,
    MAX_BYTES_BILLED,
)

logger = logging.getLogger("yukti.semantic_layer")

FORBIDDEN_SQL_PATTERNS = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bDROP\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bTRUNCATE\b",
    r"\bRENAME\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bMERGE\b",
    r"\bEXECUTE\b",
    r"\bCALL\b",
]

SEMANTIC_LAYER_PROMPT = f"""
BIGQUERY ENTERPRISE SCHEMAS & EXACT COLUMN CATALOG (Project: {GCP_PROJECT}):

0. AUTHORITATIVE SINGLE SOURCE OF TRUTH (SSOT) 360° TABLES (USE THESE FIRST FOR ALL WORKFORCE, WORK CENTRE, FIELD, CORPORATE, AND HISTOGRAM/DISTRIBUTION QUERIES):
   • `hrfin_gold.ssot_workforce_employee` (1 ROW PER EMPLOYEE — 42,171 total rows; 23,117 Active employees; ZERO fan-out):
     - Exact Columns: emp_id, emp_name, name, gender, dob, doj, fiscal_year_joined, age_years, age_band, total_tenure_years, tenure_band, social_category, category, pwd_flag, pwd_category, home_state_code, grade_id, current_grade_id, cadre ('executive'|'non_executive'|'board'), group_class, grade_designation, grade_level_order, discipline_id, discipline_code, discipline_name, discipline_function, wc_id, current_wc_id, wc_name, wc_short_name, city, state, sector, cluster_id, cluster_name, hard_station_cat, onshore_offshore, wc_type, is_corporate_hq, current_designation, entry_mode, employment_status ('Active'|'Separated'), separation_date, retirement_date, years_to_retirement, is_retiring_within_3yr, has_hard_station_tenure, has_offshore_tenure, exemption_tag, exemption_reason_code, continuous_from_date, continuous_stay_months, continuous_stay_years, is_continuous_5yr_plus, is_superannuation_exempt, cumulative_cluster_years, has_breached_cluster_10yr_cap, fy26_apar_score, fy26_apar_rating, is_dpc_eligible, fy26_training_hours, fy26_training_days, fy26_programmes_completed, fy26_gross_salary_inr, fy26_gross_salary_lakh, avg_monthly_gross_inr, fy26_overtime_hours, fy26_overtime_amount_inr, fy26_prp_inr, el_balance_days, el_encashable_days, hpl_balance_days, active_headcount (1 if active else 0), in_position_strength (1 if active else 0).
     - Example (Workforce count): `SELECT current_grade_id, cadre, COUNT(*) AS employees FROM hrfin_gold.ssot_workforce_employee WHERE active_headcount = 1 AND wc_id = 'WC-AHM' GROUP BY 1, 2 ORDER BY 3 DESC`
     - Example (Age Histogram): `SELECT CONCAT(CAST(CAST(FLOOR(age_years / 5) * 5 AS INT64) AS STRING), '-', CAST(CAST(FLOOR(age_years / 5) * 5 + 4 AS INT64) AS STRING), ' yrs') AS age_bucket, COUNT(*) AS employees FROM hrfin_gold.ssot_workforce_employee WHERE active_headcount = 1 GROUP BY FLOOR(age_years / 5), age_bucket ORDER BY FLOOR(age_years / 5)`

   • `hrfin_gold.ssot_work_centre_360` (1 ROW PER WORK CENTRE — 46 work centres; reconciles HR + Finance + Production + HSE + Governance):
     - Exact Columns: wc_id, wc_name, short_name, city, state, sector, cluster_id, hard_station_cat, onshore_offshore, wc_type, is_corporate_hq, active_headcount, in_position_strength, executive_headcount, non_executive_headcount, women_headcount, women_pct, sc_headcount, st_headcount, obc_headcount, pwd_headcount, avg_age_years, avg_tenure_years, retiring_within_3yr_count, continuous_stay_5yr_plus_execs, due_for_transfer_execs, sanctioned_strength_fy26, vacancy_count_fy26, vacancy_rate_pct_fy26, backlog_vacancies_fy26, contractor_headcount_fy26, contractor_annual_cost_inr_cr_fy26, contractor_to_regular_ratio, apprentices_engaged_fy26, payroll_gross_inr_cr_fy26, overtime_hours_fy26, overtime_cost_inr_cr_fy26, training_hours_fy26, trained_employees_fy26, avg_apar_score_fy26, hse_incidents_fy26, lti_count_fy26, ltifr_fy26, env_incidents_fy26, active_grievances_count, posh_cases_fy26, production_oil_mmt_fy26, production_gas_bcm_fy26, production_total_boe_fy26, gross_revenue_inr_cr_fy26, total_opex_inr_cr_fy26, ebitda_inr_cr_fy26, lifting_cost_per_boe_usd_fy26, manpower_cost_per_boe_usd_fy26, boe_per_employee_fy26, capex_be_inr_cr_fy26, capex_re_inr_cr_fy26, capex_actual_inr_cr_fy26, capex_utilisation_pct_fy26.
     - Example: `SELECT wc_name, active_headcount, executive_headcount, non_executive_headcount, sanctioned_strength_fy26, vacancy_count_fy26, contractor_headcount_fy26, payroll_gross_inr_cr_fy26 FROM hrfin_gold.ssot_work_centre_360 WHERE wc_id = 'WC-AHM'`

   • `hrfin_gold.ssot_field_economics_360` (1 ROW PER FIELD × FISCAL YEAR — 53 rows per year across 10 FYs):
     - Exact Columns: pnl_id, fiscal_year, field_id, field_name, basin, onshore_offshore, maturity, asset_wc_id, asset_name, oil_production_mt, gas_production_mmscm, condensate_production_mt, total_production_boe, water_cut_pct, well_downtime_hours, gas_utilisation_pct, active_producing_wells, oil_revenue_inr_cr, gas_revenue_inr_cr, gross_revenue_inr_cr, recomputed_gross_revenue_inr_cr, statutory_royalty_inr_cr, statutory_cess_inr_cr, statutory_windfall_tax_saed_inr_cr, net_revenue_inr_cr, recomputed_net_revenue_inr_cr, allocated_manpower_cost_inr_cr, total_opex_inr_cr, ebitda_inr_cr, recomputed_ebitda_inr_cr, ebitda_margin_pct, dda_depreciation_inr_cr, pbt_inr_cr, recomputed_pbt_inr_cr, lifting_cost_per_boe_usd, manpower_cost_per_boe_usd, boe_per_employee, is_loss_making_3yr_consecutive, is_divestment_candidate, pec_monetisation_potential_flag, root_cause_loss_code, reserves_2p_oil_mmt, reserves_2p_gas_bcm, reserves_2p_total_mmtoe, reserve_replacement_ratio_rrr_2p, finding_cost_usd_per_boe, development_cost_usd_per_boe, wells_drilled_count, exploratory_wells_count, development_wells_count, dry_holes_count, drilling_cost_inr_cr.

   • `hrfin_gold.ssot_corporate_annual_360` (1 ROW PER FISCAL YEAR — Corporate Macro KPIs FY18–FY27):
     - Exact Columns: fiscal_year, gross_revenue_inr_cr, offshore_revenue_inr_cr, onshore_revenue_inr_cr, statutory_levies_total_inr_cr, royalty_inr_cr, oidb_cess_inr_cr, saed_windfall_tax_inr_cr, employee_cost_total_inr_cr, operating_expenses_total_inr_cr, ebitda_inr_cr, dda_inr_cr, pbt_inr_cr, pat_inr_cr, total_capex_spent_inr_cr, dividend_per_share_inr, total_dividend_payout_inr_cr, dividend_payout_ratio_pct, lifting_cost_average_usd_boe, standalone_roce_pct, consolidated_pat_inr_cr, consolidated_roce_pct, csr_disbursed_inr_cr, csr_beneficiaries, mou_composite_score, mou_rating, receivables_outstanding_inr_cr, disputed_receivables_inr_cr, actuarial_liability_inr_cr, net_benefit_liability_inr_cr, renewable_installed_mw, renewable_generation_gwh, green_capex_inr_cr, apprentices_engaged.

1. PREFERRED PRE-AGGREGATED GOLD SUMMARY TABLES (Use these first for fastest sub-second execution):
   • `hrfin_gold.agg_headcount_tenure_summary` (PREFERRED for executive station stay & transfer queries):
     - Exact Columns: wc_id, wc_name, cluster_id, cluster_name, hard_station_cat, grade_id, discipline_id, continuous_stay_months, continuous_stay_years, total_executives, exempt_retiring_3yr, non_exempt_due_transfer.
     - Clustered by: (wc_id, continuous_stay_months).
     - Example: `SELECT grade_id, discipline_id, SUM(total_executives) as num_executives, SUM(exempt_retiring_3yr) as exempt, SUM(non_exempt_due_transfer) as due_transfer FROM hrfin_gold.agg_headcount_tenure_summary WHERE wc_id = 'WC-DEL' AND continuous_stay_months >= 60 AND grade_id LIKE 'E%' GROUP BY grade_id, discipline_id;`

   • `hrfin_gold.agg_field_pnl_summary` (PREFERRED for field P&L economics & loss-making fields):
     - Exact Columns: pnl_id, fiscal_year, field_id, field_name, basin, onshore_offshore, asset_wc_id, asset_name, oil_revenue_inr_cr, gas_revenue_inr_cr, recomputed_gross_revenue_inr_cr, statutory_royalty_inr_cr, statutory_cess_inr_cr, statutory_windfall_tax_saed_inr_cr, recomputed_net_revenue_inr_cr, allocated_manpower_cost_inr_cr, total_opex_inr_cr, recomputed_ebitda_inr_cr, recomputed_ebitda_margin_pct, dda_depreciation_inr_cr, recomputed_pbt_inr_cr, total_production_boe, lifting_cost_per_boe_usd, manpower_cost_per_boe_usd, is_loss_making_3yr_consecutive, is_divestment_candidate.
     - Clustered by: (field_id, onshore_offshore).
     - Example: `SELECT field_name, recomputed_ebitda_inr_cr, recomputed_pbt_inr_cr FROM hrfin_gold.agg_field_pnl_summary WHERE fiscal_year = 'FY26' AND (recomputed_ebitda_inr_cr < 0 OR recomputed_pbt_inr_cr < 0);`

   • `hrfin_gold.agg_lifting_cost_summary` (PREFERRED for asset lifting & manpower costs per BOE):
     - Exact Columns: fiscal_year, asset_wc_id, asset_name, onshore_offshore, total_opex_inr_cr, allocated_manpower_cost_inr_cr, total_production_boe, total_regular_headcount, total_contractor_headcount, lifting_cost_per_boe_inr, lifting_cost_per_boe_usd, manpower_cost_per_boe_usd.
     - Clustered by: (asset_wc_id, fiscal_year).
     - Example: `SELECT onshore_offshore, ROUND(SUM(total_opex_inr_cr * 10000000.0 / 88.33) / NULLIF(SUM(total_production_boe), 0), 2) as avg_lifting_cost_usd FROM hrfin_gold.agg_lifting_cost_summary WHERE fiscal_year = 'FY26' GROUP BY onshore_offshore;`

   • `hrfin_gold.agg_vacancies_summary` (PREFERRED for vacancies vs sanctioned posts across hard/remote stations):
     - Exact Columns: fiscal_year, wc_id, work_centre_name, hard_station_cat, onshore_offshore, discipline_id, total_sanctioned, total_in_position, total_vacancies, vacancy_rate_pct.
     - Clustered by: (wc_id, fiscal_year).
     - Example: `SELECT work_centre_name, SUM(total_sanctioned) as sanctioned, SUM(total_in_position) as in_position, SUM(total_vacancies) as vacancies FROM hrfin_gold.agg_vacancies_summary WHERE fiscal_year = 'FY26' AND hard_station_cat = 'C' GROUP BY work_centre_name ORDER BY vacancies DESC;`

2. BASE GOLD VIEWS & MARTS (Fallback for un-aggregated row-level details):
   • `hrfin_gold.v_continuous_stay` (Continuous Station Tenure):
     - Exact Columns: emp_id, emp_name, gender, category, dob, retirement_date, wc_id, wc_name, sector, cluster_id, cluster_name, hard_station_cat, is_corporate_hq, grade_id, discipline_id, continuous_from_date, continuous_to_date, continuous_stay_months, continuous_stay_years, is_current_stay, is_continuous_5yr_plus, is_superannuation_exempt.
     - MANDATORY: Always filter `is_current_stay = TRUE` for active postings.
     - Executive cadre: `grade_id LIKE 'E%'` (Grades E0 to E9). (No column named 'cadre').
     - Discipline column: `discipline_id` (e.g. 'DISC-DRL', 'DISC-FIN', 'DISC-HR', 'DISC-PRD', 'DISC-MM').
     - Delhi Corporate HQ: `wc_id = 'WC-DEL'`. Dehradun: `wc_id = 'WC-DDN'`. Mumbai: `wc_id = 'WC-MUM'`.
     - 5-year tenure threshold: `continuous_stay_months >= 60`.
     - Retirement Exemption (JRTP Clause 7.0, 3-year practice): `is_superannuation_exempt = TRUE` or `DATE_DIFF(retirement_date, DATE '2026-10-19', DAY) <= 3 * 365.25`.

   • `hrfin_gold.v_cluster_cumulative_tenure` (Cluster Stay Cap - JRTP Clause 4.0):
     - Exact Columns: emp_id, emp_name, gender, category, dob, retirement_date, current_grade_id, current_wc_id, cluster_id, cluster_name, cumulative_cluster_days, cumulative_cluster_years, is_currently_in_cluster, has_breached_cluster_10yr_cap, is_superannuation_exempt.
     - 10-year lifetime cluster ceiling: `cumulative_cluster_years >= 10.0` or `has_breached_cluster_10yr_cap = TRUE`.
     - Exemption status: `is_superannuation_exempt = TRUE` (within 3 years of superannuation).

   • `hrfin_gold.v_field_pnl` (Standalone Field P&L Economics):
     - Exact Columns: field_id, field_name, basin, onshore_offshore, asset_wc_id, asset_name, fiscal_year, oil_revenue_inr_cr, gas_revenue_inr_cr, recomputed_gross_revenue_inr_cr, statutory_royalty_inr_cr, statutory_cess_inr_cr, statutory_windfall_tax_saed_inr_cr, recomputed_net_revenue_inr_cr, allocated_manpower_cost_inr_cr, total_opex_inr_cr, recomputed_ebitda_inr_cr, recomputed_ebitda_margin_pct, dda_depreciation_inr_cr, recomputed_pbt_inr_cr, total_production_boe, lifting_cost_per_boe_usd, manpower_cost_per_boe_usd, boe_per_employee, is_loss_making_3yr_consecutive, is_divestment_candidate, pec_monetisation_potential_flag, root_cause_loss_code.
     - MANDATORY: Always filter `field_id IS NOT NULL` to exclude non-field corporate reconciling lines (plants/VAP/corporate).
     - In FY26, Champang (`field_id = 'FLD-CHP'`, PBT -₹4.93 Cr) is the only loss-making field.
     - Baseline fiscal year: `fiscal_year IN ('FY26', '2026')`.

   • `hrfin_gold.mart_field_economics` (Field Performance, Water Cut, Lifting Costs):
     - Exact Columns: pnl_id, fiscal_year, field_id, field_name, name, basin, onshore_offshore, line_type, asset_wc_id, wc_id, asset_name, short_name, oil_revenue_inr_cr, gas_revenue_inr_cr, gross_revenue_inr_cr, total_opex_inr_cr, ebitda_inr_cr, pbt_inr_cr, total_production_boe, lifting_cost_per_boe_usd, water_cut_pct, oil_production_mt, gas_production_mmscm.
     - Note: Water cut is `water_cut_pct` and lifting cost is `lifting_cost_per_boe_usd`. Filter `line_type = 'field'`.

   • `hrfin_gold.v_lifting_cost` (Lifting and Manpower Cost Benchmarks):
     - Exact Columns: fiscal_year, asset_wc_id, asset_name, onshore_offshore, field_id, field_name, total_production_boe, total_opex_inr_cr, lifting_cost_per_boe_inr, lifting_cost_per_boe_usd, manpower_cost_per_boe_usd, allocated_manpower_cost_inr_cr, regular_employee_headcount, contractor_headcount, boe_per_employee.
     - Baseline fiscal year: `fiscal_year IN ('FY26', '2026')`.

   • `hrfin_gold.mart_contract_workforce` (Contract Labor vs Regular Manpower & CLRA):
     - Exact Columns: contract_entry_id, contract_id, vendor_id, vendor_name, name, vendor_category, is_mse_vendor, wc_id, asset_wc_id, wc_name, short_name, state, sector, onshore_offshore, type, month, fiscal_year, service_category, discipline_id, grade_id, is_core_activity, contractor_headcount, headcount, regular_employee_count_matching, contractor_to_regular_ratio, monthly_cost_inr, contractor_cost_per_boe_usd, manpower_cost_per_boe_usd, clra_license_no, clra_compliance_status.

   • `hrfin_gold.mart_workforce` (Workforce Cadre, Superannuations, and Demographics — 1 ROW PER EMPLOYEE, 23,117 active employees total):
     - Exact Columns: emp_id, name, gender, dob, doj, fiscal_year_joined, category, social_category, pwd_flag, current_grade_id, grade_id, cadre, group, discipline_id, discipline_name, function, wc_id, wc_name, short_name, city, state, hard_station_cat, onshore_offshore, employment_status, retirement_date, years_to_retirement, is_near_retirement_2yr, is_near_retirement_3yr.
     - CRITICAL GRAIN RULE: `mart_workforce` is 1 row per employee (`emp_id` grain). To count employees in `mart_workforce`, ALWAYS use `COUNT(DISTINCT emp_id) AS employees` with `LOWER(employment_status) = 'active'` and ALWAYS group by `current_grade_id`, `cadre`, `discipline_name`, or `wc_name` so the visual shows a breakdown. NEVER use `SUM(in_position_strength)` or `SUM(sanctioned_strength)` on `mart_workforce`! For sanctioned vs in-position posts, query `hrfin_gold.agg_vacancies_summary WHERE fiscal_year = 'FY26'`.

   • `hrfin_gold.mart_capex_projects` (Major Capital Projects & Milestones):
     - Exact Columns: budget_id, fiscal_year, prj_id, project_name, sanctioned_cost_inr_cr, project_status, cost_overrun_inr_cr, schedule_slippage_months, delay_root_cause_category, asset_name, capex_utilisation_pct.

   • `hrfin_gold.mart_hse_incident` (Safety, LTIFR, and Process Safety):
     - Exact Columns: incident_id, wc_id, wc_name, onshore_offshore, incident_date, fiscal_year, incident_type, lost_time_injury_flag, days_lost, severity_tier ('Tier_1', 'Tier_2'), total_manhours_worked, calculated_ltifr, brief_description.

   • `hrfin_gold.v_headcount_asof` (Point-in-time Active Headcount View):
     - Exact Columns: as_of_date, wc_id, wc_name, sector, cluster_id, hard_station_cat, grade_id, cadre, group, discipline_id, discipline_name, gender, category, pwd_flag, active_headcount.

   • `hrfin_gold.mart_asset_productivity` (HR × Finance Asset Productivity — 1 row per asset × fiscal_year):
     - Exact Columns: asset_wc_id, asset_name, sector, onshore_offshore, fiscal_year, regular_headcount, payroll_cost_inr_cr, oil_production_mmt, gas_production_bcm, condensate_production_mmt, total_liquids_production_mmt, total_production_mmtoe, total_production_boe, gross_revenue_inr_cr, total_opex_inr_cr, ebitda_inr_cr, manpower_cost_per_boe_inr, manpower_cost_per_boe_usd, boe_per_employee, revenue_per_employee_inr_cr.

   • `hrfin_gold.mart_payroll_benefits` (Monthly Payroll, Overtime, Allowances & Benefits):
     - Exact Columns: payroll_id, emp_id, emp_name, gender, category, month, fiscal_year, wc_id, wc_name, city, sector, grade_id, cadre, designation, discipline_id, cost_centre_id, basic_pay_inr, da_inr, hra_inr, cafeteria_allowances_inr, mining_offshore_allowance_inr, overtime_hours, overtime_amount_inr, prp_inr, gross_salary_inr, net_salary_inr, employer_cpf_inr, employer_prbs_inr, employer_prmb_inr, superannuation_benefit_pct, dpe_30pct_superannuation_compliance_flag.
     - CRITICAL GRAIN RULE: `mart_payroll_benefits` is `payroll_id` (employee × month) grain. For actuarial liabilities (`benefit_liabilities`), query `hrfin_silver.benefit_liabilities` directly; for medical claims query `hrfin_silver.medical_claims`; for leave balances query `hrfin_silver.leave_ledger`.

   • `hrfin_gold.mart_postings` (Posting & Transfer History with Continuous Stay):
     - Exact Columns: posting_id, emp_id, emp_name, gender, category, wc_id, wc_name, short_name, city, sector, cluster_id, cluster_name, hard_station_cat, onshore_offshore, is_corporate_hq, from_date, to_date, fiscal_year, grade_id, current_grade_id, cadre, discipline_id, discipline_name, posting_type, order_no, tenure_months, is_current_posting, continuous_stay_months, continuous_stay_years, has_exceeded_station_5yr_cap, exemption_tag, total_transfer_cost_inr.

   • `hrfin_gold.mart_promotions_dpc` (Promotions & DPC Cases):
     - Exact Columns: promotion_id, emp_id, emp_name, gender, category, wc_id, wc_name, discipline_id, discipline_name, from_grade_id, to_grade_id, grade_id, effective_date, fiscal_year, dpc_id, promotion_mode, residency_years_completed, apar_benchmark_met, vigilance_cleared, hard_station_completed_flag, dpc_status, status, pending_reason, delay_bottleneck_reason, delay_months.

   • `hrfin_gold.mart_training_development` (Training Attendance & Programmes):
     - Exact Columns: training_record_id, emp_id, emp_name, gender, current_grade_id, grade_id, discipline_id, programme_id, programme_name, wc_id, wc_name, institute, category, start_date, end_date, fiscal_year, training_hours, training_days, completion_status, is_renewable_reskilling, training_category.

   • `hrfin_gold.mart_procurement_contracts` (Purchase Orders, GeM & MSE Procurement):
     - Exact Columns: po_line_id, po_number, vendor_id, vendor_name, vendor_category, is_mse_vendor, wc_id, wc_name, po_date, fiscal_year, service_contract_category, original_po_value_inr, revised_po_value_inr, actual_paid_amount_inr, cost_overrun_inr, overrun_reason, po_status, procurement_channel, gem_order_id, mse_vendor_social_category, is_gem_procurement, is_mse_sc_st_vendor, is_mse_women_vendor.

   • `hrfin_gold.mart_production_reserves` (Monthly Field Production & Reserves):
     - Exact Columns: prod_id, month, fiscal_year, field_id, field_name, basin, basin_name, onshore_offshore, asset_wc_id, wc_id, asset_name, oil_production_mt, gas_production_mmscm, condensate_production_mt, total_production_boe, water_cut_pct, gas_flared_mmscm, gas_utilisation_pct, active_producing_wells, well_downtime_hours, operational_uptime_pct. (For annual 2P reserves and RRR, query `hrfin_silver.reserves_annual` so monthly rows are never summed across a year).

   • `hrfin_gold.mart_employee_relations` (Grievances, Litigation, ICC & POSH Summary):
     - Exact Columns: case_id, emp_id, wc_id, wc_name, case_type, case_category, forum, filing_date, fiscal_year, status, interim_stay_granted, age_days, age_years, is_aged_over_3_years, subject_summary.

   • `hrfin_gold.mart_energy_transition` (Green Energy Projects, Solar/Wind MW & Scope 1/2 Emissions):
     - Exact Columns: transition_project_id, project_name, fiscal_year, technology_type, location_state_code, state_name, wc_id, wc_name, installed_capacity_mw, generation_gwh, scope1_avoided_emissions_mtco2e, scope2_avoided_emissions_mtco2e, annual_capex_inr_cr, cumulative_capex_inr_cr, engineers_reskilled_count, net_zero_2038_roadmap_milestone_met.

   • `hrfin_gold.mart_governance_audit` & `hrfin_gold.v_env_incidents` (Governance, Parliament, CAG, RTI, Environmental Incidents):
     - `v_env_incidents`: incident_id, date, fiscal_year, wc_id, wc_name, sector, onshore_offshore, field_id, field_name, basin, incident_type, severity, volume_released, volume_unit, regulator, notice_issued, penalty_inr_lakh, status, root_cause_category.

   • `hrfin_gold.metric_definitions` & `hrfin_gold.glossary`:
     - `metric_definitions`: metric_id, name, sql_expression, grain, unit, owner_domain, related_question_ids.
     - `glossary`: term, full_form, definition, source_document, domain, category.

2. SILVER OPERATIONAL TABLES (Authoritative single-grain tables — prefer these over multi-table marts for exact counts/sums):
   • `hrfin_silver.employee_master`: emp_id, name, gender, dob, doj, current_grade_id, discipline_id, current_wc_id, category, pwd_flag, employment_status ('Active'), retirement_date. (23,117 active employees).
   • `hrfin_silver.headcount_snapshot`: snapshot_id, month, fiscal_year, wc_id, grade_id, discipline_id, gender, category, pwd_flag, age_band, tenure_band, headcount, active_headcount, on_leave_headcount (no cadre column: executives are `grade_id LIKE 'E%'`; Monthly snapshot — filter `month = '2026-03'` for FY26 end or `month = '2026-09'` for latest Sep-2026; NEVER sum `active_headcount` across multiple months!).
   • `hrfin_silver.sanctioned_posts`: fiscal_year, wc_id, discipline_id, grade_id, sanctioned_strength, in_position_strength, vacancy_count, backlog_vacancies, special_drive_flag.
   • `hrfin_silver.posting_history`: posting_id, emp_id, wc_id, grade_id, discipline_id, designation, from_date, to_date, posting_type, order_no, is_current_posting, exemption_tag, exemption_reason_code.
   • `hrfin_silver.promotion_history` & `hrfin_silver.dpc_cases`: promotion_id/dpc_id, emp_id, from_grade_id, to_grade_id, effective_date, fiscal_year, status, delay_months, delay_bottleneck_reason.
   • `hrfin_silver.separations`: separation_id, emp_id, separation_date, fiscal_year, separation_type ('Superannuation', 'Resignation', 'VRS', 'Death'), last_grade_id, last_wc_id, exit_interview_reason.
   • `hrfin_silver.payroll_monthly`: payroll_id, emp_id, month, fiscal_year, wc_id, grade_id, basic_pay_inr, da_inr, hra_inr, cafeteria_allowances_inr, mining_offshore_allowance_inr, overtime_hours, overtime_amount_inr, prp_inr, gross_salary_inr, net_salary_inr, employer_cpf_inr, employer_prbs_inr, employer_prmb_inr.
   • `hrfin_silver.apar_ratings`: apar_id, emp_id, fiscal_year, numerical_score, final_rating, wc_id, grade_id.
   • `hrfin_silver.succession_plan`: position_id, role_title, wc_id, discipline_id, fiscal_year, criticality_tier, incumbent_emp_id, incumbent_retire_date, successor_1_emp_id, successor_1_readiness, readiness_gap_reason.
   • `hrfin_silver.training_records` & `hrfin_silver.training_calendar`: training_record_id, emp_id, programme_id, programme_name, institute, fiscal_year, training_hours, completion_status.
   • `hrfin_silver.leave_ledger`: leave_id, emp_id, fiscal_year, leave_type ('EL', 'HPL', 'CL'), transaction_type, days_count, from_date, to_date, closing_balance_days, encashable_balance_days.
   • `hrfin_silver.medical_claims` & `hrfin_silver.travel_claims`: claim_id, emp_id, wc_id, fiscal_year, claimed_amount_inr, approved_amount_inr, status, turnaround_days.
   • `hrfin_silver.grievances_litigation`, `hrfin_silver.vigilance_cases`, `hrfin_silver.posh_cases`, `hrfin_silver.icc_committees`: case/committee registers with status, filing_date, age_days, inquiry_days.
   • `hrfin_silver.apprentices`: apprentice_id, trade, trade_category, wc_id, fiscal_year, start_date, end_date, stipend_inr_month, status, category, gender (FY26 engaged = 1,550).
   • `hrfin_silver.contract_workforce`: contract_entry_id, contract_id, vendor_id, wc_id, month, fiscal_year, service_category, contractor_headcount, monthly_cost_inr, clra_compliance_status (Monthly snapshot — filter latest month or use `AVG(contractor_headcount)` per contract across months; never sum headcount across months!).
   • `hrfin_silver.hse_incidents` & `hrfin_silver.env_incidents`: safety and environmental incident logs.
   • `hrfin_silver.field_pnl_annual`, `hrfin_silver.production_monthly`, `hrfin_silver.reserves_annual`, `hrfin_silver.wells_drilled`, `hrfin_silver.cost_ledger`, `hrfin_silver.capex_budget`, `hrfin_silver.project_progress`, `hrfin_silver.purchase_orders`, `hrfin_silver.po_channel`, `hrfin_silver.receivables`, `hrfin_silver.forex_hedges`, `hrfin_silver.price_fx_monthly`.
   • `hrfin_silver.corporate_financials`, `hrfin_silver.subsidiary_financials`, `hrfin_silver.csr_projects`, `hrfin_silver.mou_targets`, `hrfin_silver.benefit_liabilities`, `hrfin_silver.energy_transition`.
   • `hrfin_silver.parliament_questions`, `hrfin_silver.cag_paras`, `hrfin_silver.rti_applications`, `hrfin_silver.board_agenda_index`, `hrfin_silver.access_audit_log`.
   • Dimensions: `hrfin_silver.dim_work_centre` (wc_id, name, short_name, city, state, sector, cluster_id, hard_station_cat, onshore_offshore, type), `hrfin_silver.dim_grade`, `hrfin_silver.dim_discipline`, `hrfin_silver.dim_field`, `hrfin_silver.dim_vendor`, `hrfin_silver.dim_project`, `hrfin_silver.dim_cost_centre`, `hrfin_silver.dim_customer`.

3. THE 5 CRITICAL QUERY-CRAFT RULES:
   Rule 1: Always use LOWER() on categoricals (e.g. `LOWER(onshore_offshore) = 'onshore'`, `LOWER(cadre) = 'executive'`, `LOWER(clra_compliance_status) = 'compliant'`).
   Rule 2: NEVER SUM OR AVG RATIOS OR PER-BARREL METRICS: Pre-computed per-barrel columns (like lifting_cost_per_boe_usd, manpower_cost_per_boe_usd) or ratios (contractor_to_regular_ratio) MUST NEVER be summed or averaged. Always recompute weighted sums:
     `lifting_cost_per_boe = ROUND(SUM(total_opex_inr_cr * 10000000.0 / 88.33) / NULLIF(SUM(total_production_boe), 0), 2)`
     `manpower_cost_per_boe = ROUND(SUM(allocated_manpower_cost_inr_cr * 10000000.0 / 88.33) / NULLIF(SUM(total_production_boe), 0), 2)`
   Rule 3: ASSET & REGIONAL RESOLUTION:
     - Offshore Regions: Western Offshore includes Mumbai High Asset (`WC-MUM`; fields `FLD-MHN`, `FLD-MHS`), Neelam & Heera (`WC-NEH`), and Bassein & Satellite (`WC-BAS`). Eastern Offshore is the Eastern Offshore Asset at Kakinada (`WC-EAS`, KG-DWN-98/2 field `FLD-KG982`). Do not label Eastern Offshore as Western Offshore.
     - Gujarat Onshore: use `state = 'Gujarat'` or `wc_id IN ('WC-AHM', 'WC-ANK', 'WC-MEH', 'WC-CAM')`. Never invent 'gujarat asset'.
     - Assam Onshore: use `state = 'Assam'` or `wc_id IN ('WC-ASM', 'WC-JOR')`.
     - North-East (NE): `sector = 'NE'` in `dim_work_centre` / `ssot_work_centre_360`, i.e. `wc_id IN ('WC-ASM', 'WC-TRI', 'WC-AAB', 'WC-JOR', 'WC-SIL', 'WC-INB')`. DO NOT equate NE with hard_station_cat='C'. Total FY26 NE executive vacancies = 143.
     - Never make unverified causal claims; cite data drivers (such as water cut or mature field age) only when present in query results.
   Rule 4: Multi-Tool Policy + Data Turns: If an inquiry involves both corporate policy rules and quantitative employee numbers (e.g. P11 retention beyond 10-year cluster cap, pre-retirement exemptions, transfer eligibility), call BOTH `search_policy` to retrieve the clause AND `query_data` to fetch exact headcounts.
   Rule 5: Rank not threshold: never use arbitrary hardcoded cutoff filters that risk returning 0 rows; use dynamic quantiles, `ORDER BY ... DESC LIMIT 10`.
"""


class SemanticLayer:
    """Manages enterprise metrics, glossary terms, and query safety."""

    def __init__(self, project_id: str = GCP_PROJECT, location: str = BQ_LOCATION):
        self.project_id = project_id
        self.location = location
        self._bq_client: Optional[bigquery.Client] = None

    @property
    def client(self) -> bigquery.Client:
        if self._bq_client is None:
            self._bq_client = bigquery.Client(
                project=self.project_id,
                location=self.location,
                default_query_job_config=bigquery.QueryJobConfig(labels=JOB_LABELS),
            )
        return self._bq_client

    def apply_query_craft_rules(self, sql: str) -> str:
        """Applies query-craft rules (LOWER on categoricals, project qualification, and row limits)."""
        refined_sql = sql

        # Case-correct categorical literals against the profiled catalog (B1.3): e.g.
        # `employment_status = 'active'` -> `'Active'` (the data's spelling), which used to return 0 rows.
        # Runs before project qualification (G4 B1 r1 finding F-1); the table regex also accepts
        # qualified names.
        refined_sql = normalize_categorical_filters(refined_sql)

        # Qualify unadorned datasets with project ID
        pattern = r"(?<![a-zA-Z0-9_\-\.`])(hrfin_gold|hrfin_silver|hrfin_docs)\.([a-zA-Z0-9_]+)"
        refined_sql = re.sub(pattern, f"`{self.project_id}`.\\1.\\2", refined_sql)


        # Case-insensitive match on categorical columns. The captured VALUE must be lowercased
        # (previously `.lower()` was applied to the replacement template, yielding e.g.
        # `LOWER(cadre) = 'Executive'`, which matches 0 rows). Stored cadre values are
        # 'executive' | 'non_executive'.
        refined_sql = re.sub(
            r"\bonshore_offshore\s*=\s*'([Oo]nshore|[Oo]ffshore)'",
            lambda m: f"LOWER(onshore_offshore) = '{m.group(1).lower()}'",
            refined_sql,
            flags=re.IGNORECASE,
        )
        refined_sql = re.sub(
            r"\bcadre\s*=\s*'(executive|non[-_ ]executive)'",
            lambda m: "LOWER(cadre) = '{}'".format(re.sub(r"[-_ ]", "_", m.group(1).lower())),
            refined_sql,
            flags=re.IGNORECASE,
        )
        # Guard against summing group-level sanctioned/in-position columns across employee-grain mart_workforce
        if "mart_workforce" in refined_sql.lower():
            refined_sql = re.sub(
                r"\bSUM\s*\(\s*(?:[a-zA-Z0-9_]+\.)?(?:in_position_strength|sanctioned_strength)\s*\)",
                "COUNT(DISTINCT emp_id)",
                refined_sql,
                flags=re.IGNORECASE,
            )

        if "LIMIT" not in refined_sql.upper() and not re.search(r"^\s*SELECT\s+COUNT\(", refined_sql, flags=re.IGNORECASE):
            # Aggregated (GROUP BY) results feed totals/insights, so a 100-row cap silently
            # produced wrong totals. Keep a generous cap for aggregates; 100 for raw row listings.
            is_aggregate = bool(re.search(r"\bGROUP\s+BY\b", refined_sql, flags=re.IGNORECASE))
            refined_sql = refined_sql.rstrip().rstrip(";") + (" LIMIT 5000;" if is_aggregate else " LIMIT 100;")
        return refined_sql

    def validate_sql_safety(self, sql: str) -> Tuple[bool, Optional[str]]:
        """Enforces SELECT-only queries, dataset allow-listing, and absence of forbidden statements."""
        sql_stripped = sql.strip().rstrip(";")
        sql_upper = sql_stripped.upper()

        if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
            return False, "Query must start with SELECT or WITH (read-only queries only)."

        for pattern in FORBIDDEN_SQL_PATTERNS:
            if re.search(pattern, sql_upper):
                return False, f"Forbidden SQL operation detected matching: {pattern}"

        matches = re.findall(r"[`]?([a-zA-Z0-9_\-]+)\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)[`]?", sql)
        for proj, dataset, table in matches:
            if dataset not in ALLOWED_DATASETS:
                return False, f"Dataset '{dataset}' is not in the allowed list: {ALLOWED_DATASETS}"

        two_part = re.findall(r"(?:FROM|JOIN)\s+[`]?([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)[`]?", sql, flags=re.IGNORECASE)
        for dataset, table in two_part:
            if dataset not in ALLOWED_DATASETS and dataset != self.project_id:
                return False, f"Dataset '{dataset}' is not in the allowed list: {ALLOWED_DATASETS}"

        return True, None

    def dry_run_check(self, sql: str) -> Tuple[bool, int, Optional[str]]:
        """Executes a dry-run to validate syntax and estimate bytes processed without incurring cost."""
        try:
            dry_job_config = bigquery.QueryJobConfig(
                dry_run=True,
                use_query_cache=False,
                labels=JOB_LABELS,
            )
            job = self.client.query(sql, job_config=dry_job_config)
            bytes_scanned = job.total_bytes_processed or 0
            if bytes_scanned > MAX_BYTES_BILLED:
                return False, bytes_scanned, f"Query would scan {bytes_scanned} bytes, exceeding cap of {MAX_BYTES_BILLED} bytes."
            return True, bytes_scanned, None
        except Exception as e:
            return False, 0, f"Dry-run syntax validation failed: {str(e)}"
