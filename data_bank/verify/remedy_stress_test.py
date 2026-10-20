import json
import os
import sys
from decimal import Decimal
from google.auth import default
from google.cloud import bigquery, discoveryengine_v1 as discoveryengine

credentials, _ = default(quota_project_id='ongc-hr-finance-agent')
bq_client = bigquery.Client(
    project='ongc-hr-finance-agent',
    credentials=credentials,
    location='asia-south1',
    default_query_job_config=bigquery.QueryJobConfig(labels={'datacloud': 'ai-agent'})
)
search_client = discoveryengine.SearchServiceClient(credentials=credentials)
serving_config = search_client.serving_config_path(
    project='ongc-hr-finance-agent',
    location='global',
    data_store='hrfin-doc-search-store',
    serving_config='default_search',
)

with open('verify/stress_test_prompts.json') as f:
    prompts = json.load(f)

# Update query craft fixes for specific prompts
for p in prompts:
    pid = p['prompt_id']

    # P_01_1: case sensitivity
    if pid == 'P_01_1':
        p['query'] = "SELECT field_name, asset_name, ROUND(AVG(water_cut_pct), 1) as avg_wc_pct, ROUND(AVG(lifting_cost_per_boe_usd), 2) as lifting_cost_usd, ROUND(SUM(water_handling_cost_inr_cr), 2) as water_handling_cr FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' AND LOWER(onshore_offshore) = 'onshore' GROUP BY 1, 2 ORDER BY avg_wc_pct DESC LIMIT 10"

    # P_02_3: case sensitivity
    if pid == 'P_02_3':
        p['query'] = "SELECT asset_name, ROUND(SUM(total_liquids_production_mt), 1) as curr_liquids_mt, ROUND(SUM(total_liquids_production_mt) * 0.05, 1) as est_incremental_mt_at_5pct_gain FROM hrfin_gold.mart_production_reserves WHERE fiscal_year = 'FY26' AND LOWER(onshore_offshore) = 'offshore' GROUP BY 1"

    # P_04_1: exploratory wells by FY on wells_drilled
    if pid == 'P_04_1':
        p['query'] = "SELECT fiscal_year, COUNT(*) as exploratory_wells, ROUND(SUM(drilling_cost_inr_cr), 2) as exploratory_cost_cr FROM hrfin_silver.wells_drilled WHERE LOWER(well_type) = 'exploratory' AND fiscal_year IN ('FY24', 'FY25', 'FY26') GROUP BY 1 ORDER BY 1"

    # P_04_2: exploratory well discovery success rate on wells_drilled
    if pid == 'P_04_2':
        p['query'] = "SELECT result_status, COUNT(*) as wells_count, ROUND(SUM(drilling_cost_inr_cr), 2) as cost_cr FROM hrfin_silver.wells_drilled WHERE fiscal_year = 'FY26' AND LOWER(well_type) = 'exploratory' GROUP BY 1"

    # P_06_1: discipline_name instead of function
    if pid == 'P_06_1':
        p['query'] = "SELECT discipline_name, COUNT(*) as retiring_within_2yr FROM hrfin_gold.mart_workforce WHERE discipline_name IN ('Geology', 'Geophysics', 'Reservoir', 'Production', 'Drilling') AND is_near_retirement_2yr = TRUE GROUP BY 1"

    # P_06_2: discipline_name and grade breakdown
    if pid == 'P_06_2':
        p['query'] = "SELECT grade_id, COUNT(*) as technical_staff FROM hrfin_gold.mart_workforce WHERE discipline_name IN ('Geology', 'Geophysics', 'Reservoir', 'Production', 'Drilling') GROUP BY 1 ORDER BY 1"

    # P_07_1: case sensitivity
    if pid == 'P_07_1':
        p['query'] = "SELECT wc_name, SUM(CASE WHEN lost_time_injury_flag THEN 1 ELSE 0 END) as lti_count, SUM(days_lost) as total_days_lost, ROUND(AVG(monthly_overtime_hours_per_worker), 1) as avg_monthly_ot_hrs, ROUND(AVG(calculated_ltifr), 3) as avg_ltifr FROM hrfin_gold.mart_hse_incident WHERE fiscal_year = 'FY26' AND LOWER(onshore_offshore) = 'onshore' GROUP BY 1 ORDER BY lti_count DESC LIMIT 5"

    # P_07_2: severity_tier format
    if pid == 'P_07_2':
        p['query'] = "SELECT incident_id, wc_name, incident_type, severity_tier, days_lost, brief_description FROM hrfin_gold.mart_hse_incident WHERE fiscal_year = 'FY26' AND severity_tier IN ('Tier_1', 'Tier_2') LIMIT 5"

    # P_10_2: hard_station_cat value
    if pid == 'P_10_2':
        p['query'] = "SELECT exemption_tag, exemption_reason_code, COUNT(*) as count_cases FROM hrfin_gold.mart_workforce WHERE hard_station_cat = 'C' AND exemption_tag IS NOT NULL GROUP BY 1, 2"

    # P_11_1: entity names without acronyms
    if pid == 'P_11_1':
        p['query'] = "SELECT fiscal_year, entity_name, pat_inr_cr, dividend_declared_inr_cr, dividend_received_by_ongc_inr_cr FROM hrfin_silver.subsidiary_financials WHERE entity_name IN ('Hindustan Petroleum Corporation Limited', 'Mangalore Refinery and Petrochemicals Limited', 'ONGC Petro additions Limited') ORDER BY entity_name, fiscal_year"

    # P_11_2: OPaL full name
    if pid == 'P_11_2':
        p['query'] = "SELECT fiscal_year, entity_name, pat_inr_cr, gross_refining_margin_usd_bbl FROM hrfin_silver.subsidiary_financials WHERE entity_name LIKE '%Petro additions%' ORDER BY fiscal_year"

    # P_12_1: wc_name for offshore platforms
    if pid == 'P_12_1':
        p['query'] = "SELECT wc_name, fiscal_year, ROUND(SUM(overtime_amount_inr)/10000000, 2) as total_ot_cr, ROUND(AVG(overtime_hours), 1) as avg_monthly_ot_hours, COUNT(DISTINCT emp_id) as employees_logged_ot FROM hrfin_gold.mart_payroll_benefits WHERE fiscal_year = 'FY26' AND wc_name LIKE '%Mumbai High%' AND overtime_amount_inr > 0 GROUP BY 1, 2"

    # P_12_2: designations in Mumbai High
    if pid == 'P_12_2':
        p['query'] = "SELECT designation, ROUND(AVG(overtime_amount_inr), 0) as avg_ot_inr, MAX(overtime_hours) as max_monthly_ot_hrs FROM hrfin_gold.mart_payroll_benefits WHERE fiscal_year = 'FY26' AND wc_name LIKE '%Mumbai High%' GROUP BY 1 ORDER BY avg_ot_inr DESC LIMIT 5"

    # P_15_1: travel_claims columns
    if pid == 'P_15_1':
        p['query'] = "SELECT to_city, COUNT(DISTINCT travel_claim_id) as claims_count, ROUND(SUM(approved_amount_inr)/10000000, 2) as total_approved_cr FROM hrfin_silver.travel_claims WHERE fiscal_year = 'FY26' GROUP BY 1 ORDER BY total_approved_cr DESC LIMIT 5"

    # P_15_2: travel_claims columns
    if pid == 'P_15_2':
        p['query'] = "SELECT grade_id, COUNT(*) as trips, ROUND(SUM(approved_amount_inr)/10000000, 2) as approved_cr, ROUND(SUM(fare_amount_inr)/10000000, 2) as fare_cr, ROUND(SUM(lodging_hotel_amount_inr)/10000000, 2) as hotel_cr, ROUND(SUM(daily_allowance_da_inr)/10000000, 2) as da_cr FROM hrfin_silver.travel_claims WHERE fiscal_year = 'FY26' AND grade_id IN ('E4', 'E5', 'E6', 'E7', 'E8') GROUP BY 1 ORDER BY 1"

    # P_15_3: travel_claims columns
    if pid == 'P_15_3':
        p['query'] = "SELECT ROUND(SUM(approved_amount_inr)/10000000, 2) as total_travel_cr, ROUND(SUM(approved_amount_inr)*0.30/10000000, 2) as savings_30pct_cr FROM hrfin_silver.travel_claims WHERE fiscal_year = 'FY26'"

    # P_17_3: join field_economics with dim_field for maturity
    if pid == 'P_17_3':
        p['query'] = "SELECT f.field_name, d.maturity, ROUND(AVG(f.lifting_cost_per_boe_usd), 2) as lifting_cost_usd, ROUND(AVG(f.water_cut_pct), 1) as avg_wc_pct FROM hrfin_gold.mart_field_economics f JOIN hrfin_silver.dim_field d ON f.field_id = d.field_id WHERE f.fiscal_year = 'FY26' GROUP BY 1, 2 ORDER BY lifting_cost_usd DESC LIMIT 5"

    # P_19_1: cadre casing
    if pid == 'P_19_1':
        p['query'] = "SELECT function, COUNT(*) as total_execs, SUM(CASE WHEN gender = 'F' THEN 1 ELSE 0 END) as women_execs, ROUND(SUM(CASE WHEN gender = 'F' THEN 1 ELSE 0 END)/COUNT(*)*100, 2) as women_pct FROM hrfin_gold.mart_workforce WHERE LOWER(cadre) = 'executive' GROUP BY 1 ORDER BY women_pct DESC"

    # P_19_2: offshore casing
    if pid == 'P_19_2':
        p['query'] = "SELECT sector, COUNT(*) as total_staff, SUM(CASE WHEN gender = 'F' THEN 1 ELSE 0 END) as women_staff, ROUND(SUM(CASE WHEN gender = 'F' THEN 1 ELSE 0 END)/COUNT(*)*100, 2) as women_pct FROM hrfin_gold.mart_workforce WHERE LOWER(onshore_offshore) = 'offshore' GROUP BY 1"

    # P_22_1: Environmental incident tracking is a true GAP in data bank
    if pid == 'P_22_1':
        p['status'] = 'GAP'
        p['query_type'] = 'NONE'
        p['query'] = ''
        p['gap_detail'] = "Environmental spills, well blowouts, and effluent discharge incidents are not modeled in silver.hse_incidents (only occupational injuries and fire incidents exist)."

    # P_23_1: status pending/stayed
    if pid == 'P_23_1':
        p['query'] = "SELECT wc_name, COUNT(DISTINCT case_id) as total_legal_cases, SUM(CASE WHEN is_aged_over_3_years THEN 1 ELSE 0 END) as aged_over_3yr FROM hrfin_gold.mart_employee_relations WHERE status IN ('pending', 'stayed') GROUP BY 1 ORDER BY total_legal_cases DESC LIMIT 5"

    # P_23_3: query vigilance_cases for sealed cover
    if pid == 'P_23_3':
        p['query'] = "SELECT vigilance_clearance_status, count(*) as count_cases FROM hrfin_silver.vigilance_cases WHERE fiscal_year = 'FY26' GROUP BY 1"

    # P_24_1: customer crude sales in receivables
    if pid == 'P_24_1':
        p['query'] = "SELECT c.name, r.product_type, ROUND(SUM(r.billed_amount_inr_cr), 2) as billed_cr FROM hrfin_silver.receivables r JOIN hrfin_silver.dim_customer c ON r.customer_id = c.customer_id WHERE r.fiscal_year = 'FY26' AND r.product_type = 'Crude Oil' GROUP BY 1, 2 ORDER BY billed_cr DESC LIMIT 5"

    # P_28_2: hard_station_cat value
    if pid == 'P_28_2':
        p['query'] = "SELECT cadre, SUM(CASE WHEN home_state_code = 'AS' THEN 1 ELSE 0 END) as assam_domicile, COUNT(*) as total_staff, ROUND(SUM(CASE WHEN home_state_code = 'AS' THEN 1 ELSE 0 END)/COUNT(*)*100, 1) as domicile_pct FROM hrfin_gold.mart_workforce WHERE hard_station_cat = 'C' GROUP BY 1"

    # P_28_3: parliament_questions in silver with state_code = 'AS'
    if pid == 'P_28_3':
        p['query'] = "SELECT question_number, subject_theme, reply_summary FROM hrfin_silver.parliament_questions WHERE state_code = 'AS' OR LOWER(brief_text) LIKE '%assam%' OR LOWER(reply_summary) LIKE '%assam%' LIMIT 3"

    # P_29_1 & P_29_2: Apprentice ledger is a true GAP (not tracked in structured tables)
    if pid == 'P_29_1':
        p['status'] = 'GAP'
        p['query_type'] = 'NONE'
        p['query'] = ''
        p['gap_detail'] = "Apprentice recruitment and engagement counts under the Apprentices Act are not modeled in structured silver tables (only public annual report citations exist in text)."
    if pid == 'P_29_2':
        p['status'] = 'GAP'
        p['query_type'] = 'NONE'
        p['query'] = ''
        p['gap_detail'] = "Trade-wise apprentice engagement quotas and stipend payments are not tracked in contract_workforce or workforce marts."

    # P_30_2: encashable_balance_days threshold (distribution max is 238 days)
    if pid == 'P_30_2':
        p['query'] = "SELECT cadre, COUNT(DISTINCT emp_id) as officers_over_200_days FROM hrfin_gold.mart_payroll_benefits WHERE fiscal_year = 'FY26' AND leave_type = 'Earned_Leave_EL' AND encashable_balance_days >= 200 GROUP BY 1"

    # P_31_1 & P_31_2: query dpc_cases for delayed cases
    if pid == 'P_31_1':
        p['query'] = "SELECT delay_bottleneck_reason, COUNT(*) as pending_count, ROUND(AVG(delay_months), 1) as avg_delay_months FROM hrfin_silver.dpc_cases WHERE status = 'delayed' GROUP BY 1 ORDER BY pending_count DESC"
    if pid == 'P_31_2':
        p['query'] = "SELECT from_grade_id, to_grade_id, COUNT(*) as cases_count FROM hrfin_silver.dpc_cases WHERE status = 'delayed' GROUP BY 1, 2 ORDER BY cases_count DESC"

    # P_32_1: Compassionate appointments is a true GAP
    if pid == 'P_32_1':
        p['status'] = 'GAP'
        p['query_type'] = 'NONE'
        p['query'] = ''
        p['gap_detail'] = "Compassionate appointment recruits are not modeled in silver.employee_master (only GATE_GT and Campus_Placement entry modes exist)."

    # P_33_1: join icc_committees with dim_work_centre
    if pid == 'P_33_1':
        p['query'] = "SELECT w.name as wc_name, i.presiding_officer_name, i.external_member_ngo, i.women_members_pct FROM hrfin_silver.icc_committees i JOIN hrfin_silver.dim_work_centre w ON i.wc_id = w.wc_id LIMIT 5"

    # P_33_2: POSH complaints is a true GAP
    if pid == 'P_33_2':
        p['status'] = 'GAP'
        p['query_type'] = 'NONE'
        p['query'] = ''
        p['gap_detail'] = "Sexual harassment (POSH) internal inquiry case register is not maintained in silver.grievances_litigation (only service and administrative grievances exist)."

    # P_35_1: disciplinary action in grievances_litigation
    if pid == 'P_35_1':
        p['query'] = "SELECT w.name as wc_name, count(*) as count_cases FROM hrfin_silver.grievances_litigation g JOIN hrfin_silver.dim_work_centre w ON g.wc_id = w.wc_id WHERE g.case_category = 'disciplinary_action' GROUP BY 1 ORDER BY count_cases DESC LIMIT 5"

    # P_35_2: disciplinary stages in vigilance_cases
    if pid == 'P_35_2':
        p['query'] = "SELECT stage, count(*) as count_cases FROM hrfin_silver.vigilance_cases GROUP BY 1"

    # P_36_1 & P_36_2: entry_mode = 'GATE_GT'
    if pid == 'P_36_1':
        p['query'] = "SELECT discipline_name, COUNT(*) as gets_count FROM hrfin_gold.mart_workforce WHERE entry_mode = 'GATE_GT' GROUP BY 1 ORDER BY gets_count DESC LIMIT 5"
    if pid == 'P_36_2':
        p['query'] = "SELECT category, COUNT(*) as trainees_count, ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(), 1) as pct FROM hrfin_gold.mart_workforce WHERE entry_mode = 'GATE_GT' GROUP BY 1"

    # P_37_1: status pending/stayed
    if pid == 'P_37_1':
        p['query'] = "SELECT forum, COUNT(*) as active_cases, SUM(CASE WHEN interim_stay_granted THEN 1 ELSE 0 END) as stay_granted_cases FROM hrfin_silver.grievances_litigation WHERE status IN ('pending', 'stayed') GROUP BY 1 ORDER BY active_cases DESC"

    # P_38_2: SC/ST & Women MSE sub-quota is a true GAP
    if pid == 'P_38_2':
        p['status'] = 'GAP'
        p['query_type'] = 'NONE'
        p['query'] = ''
        p['gap_detail'] = "Vendor master (dim_vendor) lacks SC/ST enterprise and Women-owned MSE sub-category flags required for 4% and 3% sub-target monitoring."

    # P_39_1: GeM procurement channel is a true GAP
    if pid == 'P_39_1':
        p['status'] = 'GAP'
        p['query_type'] = 'NONE'
        p['query'] = ''
        p['gap_detail'] = "Purchase orders table (silver.purchase_orders) does not track the procurement channel (GeM portal vs SAP SRM vs manual tendering)."

    # P_40_2: receivables aging >90 days
    if pid == 'P_40_2':
        p['query'] = "SELECT aging_bucket, COUNT(*) as invoices_count, ROUND(SUM(billed_amount_inr_cr - paid_amount_inr_cr), 2) as outstanding_cr FROM hrfin_silver.receivables WHERE aging_bucket IN ('>180 days', '91-180 days') GROUP BY 1"

    # P_42_2: onshore casing
    if pid == 'P_42_2':
        p['query'] = "SELECT asset_name, ROUND(SUM(gross_revenue_inr_cr), 2) as rev_cr, ROUND(SUM(total_opex_inr_cr), 2) as opex_cr, ROUND(SUM(ebitda_inr_cr), 2) as ebitda_cr, ROUND(SUM(ebitda_inr_cr)/NULLIF(SUM(gross_revenue_inr_cr),0)*100, 1) as margin_pct FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' AND LOWER(onshore_offshore) = 'onshore' GROUP BY 1 ORDER BY margin_pct ASC LIMIT 5"

    # P_43_1 & P_43_2: corporate_performance FY26
    if pid == 'P_43_1':
        p['query'] = "SELECT fiscal_year, gross_revenue_inr_cr, pat_inr_cr, standalone_roce_pct FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND gross_revenue_inr_cr IS NOT NULL LIMIT 1"
    if pid == 'P_43_2':
        p['query'] = "SELECT fiscal_year, employee_cost_total_inr_cr, gross_revenue_inr_cr, ROUND(employee_cost_total_inr_cr / NULLIF(gross_revenue_inr_cr, 0) * 100, 2) as emp_cost_pct_rev FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND gross_revenue_inr_cr IS NOT NULL LIMIT 1"

    # P_45_1: DDA in corporate_performance
    if pid == 'P_45_1':
        p['query'] = "SELECT fiscal_year, dda_inr_cr, gross_revenue_inr_cr, ROUND(dda_inr_cr / NULLIF(gross_revenue_inr_cr, 0) * 100, 1) as dda_pct_revenue FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND gross_revenue_inr_cr IS NOT NULL LIMIT 1"

    # P_45_2: exploratory dry wells on wells_drilled
    if pid == 'P_45_2':
        p['query'] = "SELECT result_status, COUNT(*) as wells_count, ROUND(SUM(drilling_cost_inr_cr), 2) as total_drilling_cost_cr FROM hrfin_silver.wells_drilled WHERE fiscal_year = 'FY26' AND LOWER(well_type) = 'exploratory' GROUP BY 1"

    # P_46_2: cost_overrun_pct threshold
    if pid == 'P_46_2':
        p['query'] = "SELECT project_name, sanctioned_cost_inr_cr, actual_spend_inr_cr, cost_overrun_inr_cr, cost_overrun_pct FROM hrfin_gold.mart_capex_projects WHERE cost_overrun_pct >= 15.0 ORDER BY cost_overrun_pct DESC LIMIT 5"

    # P_47_2: offshore casing
    if pid == 'P_47_2':
        p['query'] = "SELECT asset_name, ROUND(SUM(logistics_osv_chopper_cost_inr_cr), 2) as logistics_cr FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' AND LOWER(onshore_offshore) = 'offshore' GROUP BY 1 ORDER BY logistics_cr DESC"

    # P_49_2: onshore casing
    if pid == 'P_49_2':
        p['query'] = "SELECT field_name, asset_name, ROUND(SUM(power_fuel_cost_inr_cr), 2) as power_cost_cr, ROUND(AVG(water_cut_pct), 1) as wc_pct FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' AND LOWER(onshore_offshore) = 'onshore' GROUP BY 1, 2 ORDER BY power_cost_cr DESC LIMIT 5"

# Save updated prompts
with open('verify/stress_test_prompts_remedied.json', 'w') as f:
    json.dump(prompts, f, indent=2)

print("Saved remedied prompt definitions to verify/stress_test_prompts_remedied.json")
