import json

prompts = []

def add_p(q_num, persona, prompt_num, text, kind, status, query_type, query, gap_detail=""):
    prompts.append({
        "q_num": q_num,
        "persona": persona,
        "prompt_id": f"P_{q_num:02d}_{prompt_num}",
        "text": text,
        "kind": kind,
        "status": status,
        "query_type": query_type,
        "query": query.strip(),
        "gap_detail": gap_detail
    })

# =========================================================================
# CMD (Q01 to Q25) -> 75 prompts
# =========================================================================

# Q01: Water cut vs lifting cost across top producing onshore fields in FY26
add_p(1, "CMD", 1, "What is the correlation between water cut percentage and lifting cost across our top 10 producing onshore fields in FY26?",
      "primary (cross-silo)", "ANSWERABLE", "SQL",
      "SELECT field_name, asset_name, ROUND(AVG(water_cut_pct), 1) as avg_wc_pct, ROUND(AVG(lifting_cost_per_boe_usd), 2) as lifting_cost_usd, ROUND(SUM(water_handling_cost_inr_cr), 2) as water_handling_cr FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' AND onshore_offshore = 'Onshore' GROUP BY 1, 2 ORDER BY avg_wc_pct DESC LIMIT 10")
add_p(1, "CMD", 2, "Which fields in Mehsana and Ahmedabad have water cut exceeding 80%, and how much did they spend on water handling opex?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT field_name, asset_name, ROUND(AVG(water_cut_pct), 1) as wc_pct, ROUND(SUM(water_handling_cost_inr_cr), 2) as water_handling_cr, ROUND(SUM(total_opex_inr_cr), 2) as total_opex_cr FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' AND asset_name IN ('Mehsana Asset', 'Ahmedabad Asset') GROUP BY 1, 2 HAVING wc_pct > 80 ORDER BY wc_pct DESC")
add_p(1, "CMD", 3, "How does the water handling cost per barrel in mature Gujarat fields compare with offshore Mumbai High?",
      "compare_or_so_what", "ANSWERABLE", "SQL",
      "SELECT asset_name, ROUND(SUM(water_handling_cost_inr_cr), 2) as total_water_cost_cr, ROUND(SUM(total_production_boe), 0) as total_boe, ROUND(SUM(water_handling_cost_inr_cr) * 10000000 / NULLIF(SUM(total_production_boe), 0), 2) as water_cost_per_boe_inr FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' AND asset_name IN ('Mehsana Asset', 'Ahmedabad Asset', 'Mumbai High Asset') GROUP BY 1")

# Q02: Well downtime & uptime in Western Offshore vs Onshore
add_p(2, "CMD", 1, "Western Offshore aur Onshore assets mein kitne producing wells active hain and average downtime hours kitne hain?",
      "primary (operations)", "ANSWERABLE", "SQL",
      "SELECT onshore_offshore, COUNT(DISTINCT field_id) as fields_count, SUM(active_producing_wells) as active_wells, ROUND(SUM(well_downtime_hours), 0) as total_downtime_hrs, ROUND(AVG(operational_uptime_pct), 1) as avg_uptime_pct FROM hrfin_gold.mart_production_reserves WHERE fiscal_year = 'FY26' GROUP BY 1")
add_p(2, "CMD", 2, "What are the primary operational bottlenecks causing well downtime in Neelam & Heera asset?",
      "why", "ANSWERABLE", "SQL",
      "SELECT field_name, month, well_downtime_hours, operational_uptime_pct FROM hrfin_gold.mart_production_reserves WHERE fiscal_year = 'FY26' AND asset_name LIKE '%Neelam%' AND well_downtime_hours > 0 ORDER BY well_downtime_hours DESC LIMIT 5")
add_p(2, "CMD", 3, "Agar hum Western Offshore mein 5% uptime improve karein, what is the estimated incremental liquids production?",
      "what_if", "ANSWERABLE", "SQL",
      "SELECT asset_name, ROUND(SUM(total_liquids_production_mt), 1) as curr_liquids_mt, ROUND(SUM(total_liquids_production_mt) * 0.05, 1) as est_incremental_mt_at_5pct_gain FROM hrfin_gold.mart_production_reserves WHERE fiscal_year = 'FY26' AND onshore_offshore = 'Offshore' GROUP BY 1")

# Q03: Processing plants contract workforce ratio & spend
add_p(3, "CMD", 1, "What is the ratio of contract workforce to regular employees in our major processing plants (Uran and Hazira)?",
      "primary (people+money)", "ANSWERABLE", "SQL",
      "SELECT wc_name, SUM(headcount) as contractor_count, MAX(regular_employee_count_matching) as regular_count, ROUND(SUM(headcount) / NULLIF(MAX(regular_employee_count_matching), 0), 2) as contractor_ratio, ROUND(SUM(monthly_cost_inr)/10000000, 2) as annual_contract_spend_cr FROM hrfin_gold.mart_contract_workforce WHERE fiscal_year = 'FY26' AND (wc_name LIKE '%Hazira%' OR wc_name LIKE '%Uran%') GROUP BY 1")
add_p(3, "CMD", 2, "Hazira Plant contract spend kitna hai and what percentage goes to Micro and Small Enterprise (MSE) vendors?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT is_mse_vendor, COUNT(DISTINCT vendor_id) as vendors, SUM(headcount) as total_contractors, ROUND(SUM(monthly_cost_inr)/10000000, 2) as cost_cr FROM hrfin_gold.mart_contract_workforce WHERE fiscal_year = 'FY26' AND wc_name LIKE '%Hazira%' GROUP BY 1")
add_p(3, "CMD", 3, "Are any contract agencies deployed at Hazira or Uran operating with non-compliant CLRA licenses?",
      "risk_compliance", "ANSWERABLE", "SQL",
      "SELECT wc_name, clra_compliance_status, COUNT(DISTINCT contract_id) as contracts_count FROM hrfin_gold.mart_contract_workforce WHERE (wc_name LIKE '%Hazira%' OR wc_name LIKE '%Uran%') GROUP BY 1, 2")

# Q04: Exploratory drilling track record across 3 years
add_p(4, "CMD", 1, "MoPNG review prep: How many exploratory wells were drilled vs exploratory drilling expenditure across FY24, FY25, and FY26?",
      "primary (ministry_prep)", "ANSWERABLE", "SQL",
      "SELECT fiscal_year, SUM(CASE WHEN well_type = 'Exploratory' THEN 1 ELSE 0 END) as exploratory_wells, ROUND(SUM(CASE WHEN well_type = 'Exploratory' THEN drilling_cost_inr_cr ELSE 0 END), 2) as exploratory_cost_cr FROM hrfin_gold.mart_production_reserves GROUP BY 1 ORDER BY 1")
add_p(4, "CMD", 2, "Of the exploratory wells drilled in FY26, what was the discovery success rate versus dry wells?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT result_status, COUNT(*) as wells_count, ROUND(SUM(drilling_cost_inr_cr), 2) as cost_cr FROM hrfin_gold.mart_production_reserves WHERE fiscal_year = 'FY26' AND well_type = 'Exploratory' GROUP BY 1")
add_p(4, "CMD", 3, "What was the average finding cost per BOE across Frontier vs KG basins over the last 3 years?",
      "compare_or_so_what", "ANSWERABLE", "SQL",
      "SELECT basin_name, fiscal_year, ROUND(AVG(finding_cost_usd_per_boe), 2) as avg_finding_cost_usd, ROUND(AVG(reserve_replacement_ratio_rrr_2p), 2) as avg_rrr FROM hrfin_gold.mart_production_reserves WHERE basin_name IN ('KG-PG Basin', 'Frontier Basin') GROUP BY 1, 2 ORDER BY 1, 2")

# Q05: Renewable energy capex and capacity under OGL
add_p(5, "CMD", 1, "What is our cumulative capital expenditure in renewable energy projects under ONGC Green Limited (OGL), and current installed capacity?",
      "primary (energy_transition)", "ANSWERABLE", "SQL",
      "SELECT technology_type, COUNT(DISTINCT transition_project_id) as projects, SUM(installed_capacity_mw) as capacity_mw, ROUND(SUM(annual_capex_inr_cr), 2) as capex_fy26_cr, ROUND(MAX(cumulative_capex_inr_cr), 2) as cumulative_capex_cr FROM hrfin_gold.mart_energy_transition WHERE fiscal_year = 'FY26' GROUP BY 1")
add_p(5, "CMD", 2, "What is the annual Scope 1 and Scope 2 avoided emissions (in MTCO2e) achieved from operational renewable projects?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT fiscal_year, ROUND(SUM(generation_gwh), 1) as gen_gwh, ROUND(SUM(scope1_avoided_emissions_mtco2e), 1) as scope1_avoided, ROUND(SUM(scope2_avoided_emissions_mtco2e), 1) as scope2_avoided FROM hrfin_gold.mart_energy_transition GROUP BY 1 ORDER BY 1")
add_p(5, "CMD", 3, "Are our renewable projects meeting the Net Zero 2038 interim roadmap milestones?",
      "what_if_target", "ANSWERABLE", "SQL",
      "SELECT technology_type, net_zero_2038_roadmap_milestone_met, COUNT(*) as milestones_count FROM hrfin_gold.mart_energy_transition WHERE fiscal_year = 'FY26' GROUP BY 1, 2")

# Q06: Technical retirement vs junior engineering base
add_p(6, "CMD", 1, "How many petroleum engineers and geoscientists are retiring within 2 years, and what is our junior vs senior cadre distribution?",
      "primary (workforce_silo)", "ANSWERABLE", "SQL",
      "SELECT function, COUNT(*) as retiring_within_2yr FROM hrfin_gold.mart_workforce WHERE function IN ('Geosciences', 'Drilling', 'Production', 'Reservoir') AND is_near_retirement_2yr = TRUE GROUP BY 1")
add_p(6, "CMD", 2, "Break down the core technical workforce in subsurface disciplines across executive grades (E1-E4 vs E5-E9).",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT cadre, group, COUNT(*) as technical_staff FROM hrfin_gold.mart_workforce WHERE function IN ('Geosciences', 'Drilling', 'Production', 'Reservoir') GROUP BY 1, 2 ORDER BY 1, 2")
add_p(6, "CMD", 3, "Why has the induction rate through GATE not kept pace with superannuation vacancies in subsurface disciplines?",
      "why_policy", "PARTIAL", "SQL",
      "SELECT entry_mode, COUNT(*) as total_intake FROM hrfin_gold.mart_workforce WHERE function IN ('Geosciences', 'Drilling', 'Production', 'Reservoir') GROUP BY 1",
      "Historical DPE/MoPNG approved recruitment ceilings and annual vacancy sanction notes are not stored as tabular fields.")

# Q07: Safety LTI and overtime correlation
add_p(7, "CMD", 1, "Which onshore work centres recorded the highest number of lost time injuries (LTI) in FY26, and was there high monthly overtime?",
      "primary (hse_risk)", "ANSWERABLE", "SQL",
      "SELECT wc_name, SUM(CASE WHEN lost_time_injury_flag THEN 1 ELSE 0 END) as lti_count, SUM(days_lost) as total_days_lost, ROUND(AVG(monthly_overtime_hours_per_worker), 1) as avg_monthly_ot_hrs, ROUND(AVG(calculated_ltifr), 3) as avg_ltifr FROM hrfin_gold.mart_hse_incident WHERE fiscal_year = 'FY26' AND onshore_offshore = 'Onshore' GROUP BY 1 ORDER BY lti_count DESC LIMIT 5")
add_p(7, "CMD", 2, "Did any Tier-1 process safety incidents or fatalities occur in Assam Asset or Western Offshore during FY26?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT incident_id, wc_name, incident_type, severity_tier, days_lost, brief_description FROM hrfin_gold.mart_hse_incident WHERE fiscal_year = 'FY26' AND severity_tier IN ('Tier 1', 'Tier 2') LIMIT 5")
add_p(7, "CMD", 3, "Under ONGC Safety Policy, what mandatory root cause analysis and board reporting is triggered after a Tier-1 incident?",
      "policy_search", "ANSWERABLE", "SEARCH",
      "mandatory root cause analysis reporting to board for Tier 1 safety incidents")

# Q08: Top open CAG audit paras with highest financial implication
add_p(8, "CMD", 1, "What are the top 5 CAG audit paras currently open against ONGC with the highest financial implication?",
      "primary (governance)", "ANSWERABLE", "SQL",
      "SELECT cag_para_id, reference_number, subject_title, authority_or_department, financial_implication_inr_cr, current_status FROM hrfin_gold.mart_governance_audit WHERE record_type = 'cag_para' ORDER BY financial_implication_inr_cr DESC LIMIT 5")
add_p(8, "CMD", 2, "Which operating departments (Drilling, Offshore Logistics, MM, Finance) have audit paras pending resolution for more than 3 years?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT authority_or_department, COUNT(*) as paras_over_3yr, ROUND(SUM(financial_implication_inr_cr), 2) as total_financial_implication_cr FROM hrfin_gold.mart_governance_audit WHERE record_type = 'cag_para' AND is_aged_over_3_years = TRUE GROUP BY 1 ORDER BY paras_over_3yr DESC")
add_p(8, "CMD", 3, "What is the Action Taken Report (ATR) submission status to the Ministry / PAC for these high-value paras?",
      "compare_or_so_what", "ANSWERABLE", "SQL",
      "SELECT current_status, COUNT(*) as paras_count, ROUND(SUM(financial_implication_inr_cr), 2) as total_implication_cr FROM hrfin_gold.mart_governance_audit WHERE record_type = 'cag_para' GROUP BY 1")

# Q09: Gas sales realisation: APM vs Premium pricing
add_p(9, "CMD", 1, "What is our total natural gas revenue share vs crude oil revenue in FY26 across onshore and offshore segments?",
      "primary (gas_economics)", "ANSWERABLE", "SQL",
      "SELECT fiscal_year, ROUND(SUM(gas_revenue_inr_cr), 2) as total_gas_rev_cr, ROUND(SUM(oil_revenue_inr_cr), 2) as total_oil_rev_cr, ROUND(SUM(gas_revenue_inr_cr) / NULLIF(SUM(gross_revenue_inr_cr), 0) * 100, 1) as gas_rev_share_pct FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' GROUP BY 1")
add_p(9, "CMD", 2, "What is the implied revenue realisation difference per SCM between Mumbai High and Eastern Offshore deepwater gas?",
      "compare", "ANSWERABLE", "SQL",
      "SELECT asset_name, ROUND(SUM(gas_revenue_inr_cr), 2) as gas_rev_cr, ROUND(SUM(gas_production_mmscm), 1) as gas_vol_mmscm, ROUND(SUM(gas_revenue_inr_cr)*10 / NULLIF(SUM(gas_production_mmscm), 0), 2) as implied_realisation_inr_scm FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' AND asset_name IN ('Mumbai High Asset', 'Eastern Offshore Asset') GROUP BY 1")
add_p(9, "CMD", 3, "How are domestic APM gas ceiling and new-well gas pricing defined under government gas guidelines?",
      "policy_glossary", "ANSWERABLE", "SQL",
      "SELECT term, full_form, definition FROM hrfin_gold.glossary WHERE term IN ('BCM', 'BOE', 'MMSCMD')")

# Q10: Assam medical exemptions and compassionate transfers
add_p(10, "CMD", 1, "Assam asset mein kitne executives ne posting ke baad medical ground par exemption ya premature transfer manga hai?",
      "primary (people_friction)", "ANSWERABLE", "SQL",
      "SELECT exemption_tag, count(*) as count_execs FROM hrfin_gold.mart_workforce WHERE (wc_name LIKE '%Assam%' OR wc_name LIKE '%Nazira%' OR wc_name LIKE '%Sivasagar%') AND exemption_tag IS NOT NULL GROUP BY 1")
add_p(10, "CMD", 2, "What are the specific exemption reason codes recorded in SAP for officers posted at Category-C hard stations?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT exemption_tag, exemption_reason_code, COUNT(*) as count_cases FROM hrfin_gold.mart_workforce WHERE hard_station_cat IN ('Category C', 'Hard Station') AND exemption_tag IS NOT NULL GROUP BY 1, 2")
add_p(10, "CMD", 3, "Under JRTP, can an officer be transferred prematurely before completing 3 years on compassionate grounds?",
      "policy_search", "ANSWERABLE", "SEARCH",
      "can an officer be transferred before completing three years in case of administrative emergency or medical")

# Q11: Subsidiary dividends and OPaL equity return
add_p(11, "CMD", 1, "What has been the cash dividend return to ONGC from HPCL, MRPL, and OPaL over the last 3 fiscal years relative to our equity investments?",
      "primary (subsidiaries)", "ANSWERABLE", "SQL",
      "SELECT fiscal_year, entity_name, subsidiary_pat_inr_cr, dividend_declared_inr_cr, dividend_received_by_ongc_inr_cr FROM hrfin_silver.subsidiary_financials WHERE entity_name IN ('Hindustan Petroleum Corporation Limited (HPCL)', 'Mangalore Refinery and Petrochemicals Limited (MRPL)', 'ONGC Petro additions Limited (OPaL)') ORDER BY entity_name, fiscal_year")
add_p(11, "CMD", 2, "What is OPaL's net profit/loss and gross refining/petrochemical margin performance over the last 3 years?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT fiscal_year, entity_name, subsidiary_pat_inr_cr, gross_refining_margin_usd_bbl FROM hrfin_silver.subsidiary_financials WHERE entity_name LIKE '%OPaL%' ORDER BY fiscal_year")
add_p(11, "CMD", 3, "What are the formal contractual covenants governing debt-to-equity restructuring of OPaL with lenders?",
      "strategic_legal", "GAP", "NONE",
      "", "Confidential loan restructuring term sheet between ONGC, OPaL, and consortium lenders (SBI/PNB) is not indexed in the data bank.")

# Q12: Offshore platform overtime cost vs staffing
add_p(12, "CMD", 1, "What is the total overtime payout (INR Cr) across offshore production platforms in Mumbai High, and how many employees logged OT?",
      "primary (cross-silo)", "ANSWERABLE", "SQL",
      "SELECT wc_name, fiscal_year, ROUND(SUM(overtime_amount_inr)/10000000, 2) as total_ot_cr, ROUND(AVG(overtime_hours), 1) as avg_monthly_ot_hours, COUNT(DISTINCT emp_id) as employees_logged_ot FROM hrfin_gold.mart_payroll_benefits WHERE fiscal_year = 'FY26' AND sector = 'Western Offshore' AND overtime_amount_inr > 0 GROUP BY 1, 2")
add_p(12, "CMD", 2, "Which technical designations in Western Offshore have the highest monthly overtime payout per employee?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT designation, ROUND(AVG(overtime_amount_inr), 0) as avg_ot_inr, MAX(overtime_hours) as max_monthly_ot_hrs FROM hrfin_gold.mart_payroll_benefits WHERE fiscal_year = 'FY26' AND sector = 'Western Offshore' GROUP BY 1 ORDER BY avg_ot_inr DESC LIMIT 5")
add_p(12, "CMD", 3, "What-if: Would hiring 100 additional regular offshore production technicians reduce net annual overtime costs?",
      "what_if", "ANSWERABLE", "SQL",
      "SELECT ROUND(SUM(overtime_amount_inr)/10000000, 2) as total_offshore_ot_cr, ROUND(100 * 2200000 / 10000000, 2) as cost_of_100_technicians_cr FROM hrfin_gold.mart_payroll_benefits WHERE fiscal_year = 'FY26' AND sector = 'Western Offshore'")

# Q13: CSR in Aspirational Districts vs Field Areas
add_p(13, "CMD", 1, "What was our total CSR expenditure in Aspirational Districts during FY26, and how many districts were covered?",
      "primary (csr_governance)", "ANSWERABLE", "SQL",
      "SELECT is_aspirational_district, COUNT(DISTINCT district_name) as districts, ROUND(SUM(actual_disbursed_inr_cr), 2) as disbursed_cr FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND actual_disbursed_inr_cr IS NOT NULL GROUP BY 1")
add_p(13, "CMD", 2, "Which specific districts in Assam, Andhra Pradesh, and Gujarat received the highest CSR allocations?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT state_code, district_name, is_aspirational_district, ROUND(SUM(actual_disbursed_inr_cr), 2) as spend_cr FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND is_aspirational_district = TRUE GROUP BY 1, 2, 3 ORDER BY spend_cr DESC LIMIT 5")
add_p(13, "CMD", 3, "What percentage of our total CSR spend is deployed in operational field areas versus general districts?",
      "compare_or_so_what", "ANSWERABLE", "SQL",
      "SELECT is_operational_field_area, ROUND(SUM(actual_disbursed_inr_cr), 2) as spend_cr, ROUND(SUM(actual_disbursed_inr_cr)/MAX(total_csr_spend_inr_cr)*100, 1) as pct_of_total FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND actual_disbursed_inr_cr IS NOT NULL GROUP BY 1")

# Q14: Natural gas flaring volume and utilisation efficiency
add_p(14, "CMD", 1, "How much natural gas was flared or vented across our installations in FY26, and what was the average gas utilisation efficiency?",
      "primary (flaring_efficiency)", "ANSWERABLE", "SQL",
      "SELECT onshore_offshore, ROUND(SUM(gas_production_mmscm), 1) as total_gas_mmscm, ROUND(SUM(gas_flared_mmscm), 1) as flared_mmscm, ROUND(SUM(gas_flared_mmscm)/NULLIF(SUM(gas_production_mmscm),0)*100, 2) as flaring_pct, ROUND(AVG(gas_utilisation_pct), 1) as avg_utilisation_pct FROM hrfin_gold.mart_production_reserves WHERE fiscal_year = 'FY26' GROUP BY 1")
add_p(14, "CMD", 2, "Which assets have gas flaring rates exceeding 2% of total production?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT asset_name, ROUND(SUM(gas_production_mmscm), 1) as prod_mmscm, ROUND(SUM(gas_flared_mmscm), 1) as flared_mmscm, ROUND(SUM(gas_flared_mmscm)/NULLIF(SUM(gas_production_mmscm),0)*100, 2) as flaring_pct FROM hrfin_gold.mart_production_reserves WHERE fiscal_year = 'FY26' GROUP BY 1 HAVING flaring_pct > 2.0 ORDER BY flaring_pct DESC")
add_p(14, "CMD", 3, "What is the estimated lost revenue (in ₹ Cr) from flared gas in Assam and Western Onshore assets?",
      "compare_or_so_what", "ANSWERABLE", "SQL",
      "SELECT asset_name, ROUND(SUM(gas_flared_mmscm), 1) as flared_mmscm, ROUND(SUM(gas_flared_mmscm) * 10 * 8.5 / 10, 2) as est_lost_revenue_cr FROM hrfin_gold.mart_production_reserves WHERE fiscal_year = 'FY26' AND asset_name IN ('Assam Asset', 'Ahmedabad Asset', 'Mehsana Asset') GROUP BY 1")

# Q15: Executive travel expenditure (TA/DA claims)
add_p(15, "CMD", 1, "How much has ONGC approved in travel claims (TA/DA) across major hubs (Delhi, Dehradun, Mumbai) in FY26?",
      "primary (people+money)", "ANSWERABLE", "SQL",
      "SELECT to_city, COUNT(DISTINCT travel_claim_id) as claims_count, ROUND(SUM(claimed_amount_inr)/10000000, 2) as claimed_cr, ROUND(SUM(approved_amount_inr)/10000000, 2) as approved_cr FROM hrfin_silver.travel_claims WHERE fiscal_year = 'FY26' GROUP BY 1 ORDER BY approved_cr DESC LIMIT 5")
add_p(15, "CMD", 2, "What is the travel claim expenditure breakdown across executive grades E4-E8?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT grade_id, COUNT(*) as trips, ROUND(SUM(approved_amount_inr)/10000000, 2) as approved_cr FROM hrfin_silver.travel_claims WHERE fiscal_year = 'FY26' AND grade_id IN ('E4', 'E5', 'E6', 'E7', 'E8') GROUP BY 1 ORDER BY 1")
add_p(15, "CMD", 3, "What-if: If inter-city corporate travel is reduced by 30% via video conferencing, what is the annual financial savings?",
      "what_if", "ANSWERABLE", "SQL",
      "SELECT ROUND(SUM(approved_amount_inr)/10000000, 2) as total_travel_cr, ROUND(SUM(approved_amount_inr)*0.30/10000000, 2) as savings_30pct_cr FROM hrfin_silver.travel_claims WHERE fiscal_year = 'FY26'")

# Q16: RTI applications disposal compliance
add_p(16, "CMD", 1, "How many RTI applications were received in FY26 across operating departments, and what was the statutory 30-day disposal rate?",
      "primary (governance)", "ANSWERABLE", "SQL",
      "SELECT operating_department, COUNT(*) as total_rtis, SUM(CASE WHEN is_within_30_days_statutory THEN 1 ELSE 0 END) as disposed_within_30d, ROUND(SUM(CASE WHEN is_within_30_days_statutory THEN 1 ELSE 0 END)/COUNT(*)*100, 1) as compliance_pct FROM hrfin_silver.rti_applications WHERE fiscal_year = 'FY26' GROUP BY 1 ORDER BY total_rtis DESC")
add_p(16, "CMD", 2, "What is the average turnaround time in days for RTI applications by applicant category?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT applicant_category, COUNT(*) as rtis, ROUND(AVG(turnaround_days), 1) as avg_days FROM hrfin_silver.rti_applications WHERE fiscal_year = 'FY26' GROUP BY 1")
add_p(16, "CMD", 3, "Under RTI Act guidelines, what exemptions are invoked when refusing disclosure of internal vigilance inquiry details?",
      "policy_search", "ANSWERABLE", "SEARCH",
      "confidentiality of preliminary inquiries disciplinary investigations CVC vigilance")

# Q17: Secondary recovery (IOR/EOR) spend in Gujarat
add_p(17, "CMD", 1, "Mehsana aur Ankleshwar assets mein mature fields par secondary recovery (IOR/EOR) capex kitna spend hua in FY26?",
      "primary (field_capex)", "ANSWERABLE", "SQL",
      "SELECT asset_name, fiscal_year, ROUND(SUM(secondary_recovery_capex_inr_cr), 2) as ior_eor_capex_cr, ROUND(SUM(actual_spend_inr_cr), 2) as total_actual_spend_cr FROM hrfin_gold.mart_capex_projects WHERE asset_name IN ('Mehsana Asset', 'Ankleshwar Asset') AND fiscal_year = 'FY26' GROUP BY 1, 2")
add_p(17, "CMD", 2, "How many active water/polymer injection wells are operational in Mehsana and Ankleshwar to support pressure maintenance?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT asset_name, SUM(active_producing_wells) as prod_wells, SUM(active_injection_wells) as inj_wells, ROUND(SUM(total_liquids_production_mt), 1) as liquids_mt FROM hrfin_gold.mart_production_reserves WHERE fiscal_year = 'FY26' AND asset_name IN ('Mehsana Asset', 'Ankleshwar Asset') GROUP BY 1")
add_p(17, "CMD", 3, "What is the lifting cost per barrel in fields categorized under tertiary EOR versus standard mature fields?",
      "compare_or_so_what", "ANSWERABLE", "SQL",
      "SELECT field_name, maturity, ROUND(AVG(lifting_cost_per_boe_usd), 2) as lifting_cost_usd, ROUND(AVG(water_cut_pct), 1) as avg_wc_pct FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' AND asset_name IN ('Mehsana Asset', 'Ankleshwar Asset') GROUP BY 1, 2 ORDER BY lifting_cost_usd DESC LIMIT 5")

# Q18: High spend vendor concentration and overruns
add_p(18, "CMD", 1, "Which top 5 procurement vendor categories accounted for the highest contract value and cost overruns in FY26?",
      "primary (commercial)", "ANSWERABLE", "SQL",
      "SELECT service_contract_category, COUNT(DISTINCT po_number) as po_count, ROUND(SUM(actual_paid_amount_inr)/10000000, 2) as paid_cr, ROUND(SUM(cost_overrun_inr)/10000000, 2) as overrun_cr FROM hrfin_gold.mart_procurement_contracts WHERE fiscal_year = 'FY26' GROUP BY 1 ORDER BY paid_cr DESC LIMIT 5")
add_p(18, "CMD", 2, "Who are our top 5 individual vendors by total paid amount in FY26 and what was their contract cost overrun percentage?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT vendor_name, vendor_category, is_mse_vendor, COUNT(DISTINCT po_number) as pos, ROUND(SUM(actual_paid_amount_inr)/10000000, 2) as total_spend_cr, ROUND(SUM(cost_overrun_inr)/10000000, 2) as total_overrun_cr FROM hrfin_gold.mart_procurement_contracts WHERE fiscal_year = 'FY26' GROUP BY 1, 2, 3 ORDER BY total_spend_cr DESC LIMIT 5")
add_p(18, "CMD", 3, "What powers does the CMD have under the Book of Delegated Powers to approve contract cost variations above 10%?",
      "policy_powers", "ANSWERABLE", "SEARCH",
      "who has the sanction authority to approve high value drilling contracts above fifty crore rupees")

# Q19: Women representation across engineering disciplines
add_p(19, "CMD", 1, "What is the distribution of women executives across core engineering disciplines (Drilling, Production, Reservoir) versus support functions?",
      "primary (diversity)", "ANSWERABLE", "SQL",
      "SELECT function, COUNT(*) as total_execs, SUM(CASE WHEN gender = 'F' THEN 1 ELSE 0 END) as women_execs, ROUND(SUM(CASE WHEN gender = 'F' THEN 1 ELSE 0 END)/COUNT(*)*100, 2) as women_pct FROM hrfin_gold.mart_workforce WHERE cadre = 'Executive' GROUP BY 1 ORDER BY women_pct DESC")
add_p(19, "CMD", 2, "What is the percentage of women employees currently posted at offshore installations across Western and Eastern Offshore?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT sector, COUNT(*) as total_staff, SUM(CASE WHEN gender = 'F' THEN 1 ELSE 0 END) as women_staff, ROUND(SUM(CASE WHEN gender = 'F' THEN 1 ELSE 0 END)/COUNT(*)*100, 2) as women_pct FROM hrfin_gold.mart_workforce WHERE onshore_offshore = 'Offshore' GROUP BY 1")
add_p(19, "CMD", 3, "What special daily allowance and travel provisions apply for employees deployed on 14-day offshore shift cycles?",
      "policy_search", "ANSWERABLE", "SEARCH",
      "what is the daily allowance and hardship pay for offshore platform duty")

# Q20: Foreign exchange unhedged exposure and FX risk
add_p(20, "CMD", 1, "What is our net foreign currency exposure on dollar-denominated charter hire of drilling rigs and services in FY26?",
      "primary (forex_risk)", "ANSWERABLE", "SQL",
      "SELECT currency_pair, underlying_contract_category, ROUND(SUM(gross_exposure_usd)/1000000, 2) as gross_exp_usd_m, ROUND(SUM(hedged_amount_usd)/1000000, 2) as hedged_usd_m, ROUND(SUM(unhedged_exposure_usd)/1000000, 2) as unhedged_usd_m, ROUND(AVG(hedge_ratio_pct), 1) as avg_hedge_ratio FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND gross_exposure_usd IS NOT NULL GROUP BY 1, 2")
add_p(20, "CMD", 2, "What is our company-wide hedge ratio on foreign exchange risk in FY26?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT currency_pair, ROUND(SUM(hedged_amount_usd)/NULLIF(SUM(gross_exposure_usd), 0)*100, 1) as portfolio_hedge_ratio_pct FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND gross_exposure_usd IS NOT NULL GROUP BY 1")
add_p(20, "CMD", 3, "What-if: If USD/INR depreciates by 5%, what is the estimated additional expenditure on unhedged dollar contracts in INR Cr?",
      "what_if", "ANSWERABLE", "SQL",
      "SELECT ROUND(SUM(unhedged_exposure_usd)/1000000, 2) as unhedged_m_usd, ROUND(SUM(unhedged_exposure_usd) * 86.0 * 0.05 / 10000000, 2) as additional_cost_5pct_depreciation_inr_cr FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND gross_exposure_usd IS NOT NULL")

# Q21: PEC candidates and marginal field monetization
add_p(21, "CMD", 1, "Which mature marginal fields have been identified with positive PEC monetization potential flag in FY26?",
      "primary (monetization)", "ANSWERABLE", "SQL",
      "SELECT field_name, asset_name, onshore_offshore, pec_monetisation_potential_flag, is_divestment_candidate, is_loss_making_3yr_consecutive, root_cause_loss_code FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' AND pec_monetisation_potential_flag = TRUE ORDER BY asset_name, field_name")
add_p(21, "CMD", 2, "What are the projected 5-year opex and capex savings if the candidate marginal fields are monetised via PEC contracts?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT asset_name, COUNT(DISTINCT field_id) as pec_fields, ROUND(SUM(estimated_annual_opex_savings_inr_cr), 2) as annual_opex_savings_cr, ROUND(SUM(estimated_annual_capex_savings_inr_cr), 2) as annual_capex_savings_cr, ROUND(SUM(projected_pec_farmout_payoff_5yr_inr_cr), 2) as payoff_5yr_cr FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' AND pec_monetisation_potential_flag = TRUE GROUP BY 1")
add_p(21, "CMD", 3, "Can the agent retrieve the confidential Board note regarding production enhancement contracts for marginal fields?",
      "document_request", "ANSWERABLE", "SEARCH",
      "what is the delegation of power for entering into production enhancement contracts on mature fields")

# Q22: Environmental incidents & spills
add_p(22, "CMD", 1, "How many environmental and blowout incidents were logged across onshore and offshore assets in FY26?",
      "primary (hse_env)", "ANSWERABLE", "SQL",
      "SELECT incident_type, severity_tier, COUNT(*) as incident_count, SUM(days_lost) as days_lost FROM hrfin_gold.mart_hse_incident WHERE fiscal_year = 'FY26' AND incident_type LIKE '%Environmental%' GROUP BY 1, 2")
add_p(22, "CMD", 2, "Which work centres logged major fire or blowout incidents in FY26?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT wc_name, incident_type, COUNT(*) as incidents, brief_description FROM hrfin_gold.mart_hse_incident WHERE fiscal_year = 'FY26' AND (incident_type LIKE '%Blowout%' OR incident_type LIKE '%Fire%') GROUP BY 1, 2, 4")
add_p(22, "CMD", 3, "What were the specific pollution control board penalty amounts levied against Gujarat onshore installations in FY26?",
      "statutory_fines", "GAP", "NONE",
      "", "State Pollution Control Board fine and consent-to-operate penalty ledger is not tracked as a distinct column in the data bank.")

# Q23: Work centres with highest legal grievances & vigilance cases
add_p(23, "CMD", 1, "Which work centres currently have the highest number of active employee litigation cases and service grievances?",
      "primary (legal_vigilance)", "ANSWERABLE", "SQL",
      "SELECT wc_name, COUNT(DISTINCT case_id) as total_legal_cases, SUM(CASE WHEN is_aged_over_3_years THEN 1 ELSE 0 END) as aged_over_3yr FROM hrfin_gold.mart_employee_relations WHERE status = 'Active' GROUP BY 1 ORDER BY total_legal_cases DESC LIMIT 5")
add_p(23, "CMD", 2, "How many of the active legal cases involve seniority and promotion disputes versus disciplinary actions?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT case_type, case_category, COUNT(*) as cases_count FROM hrfin_gold.mart_employee_relations GROUP BY 1, 2 ORDER BY cases_count DESC")
add_p(23, "CMD", 3, "How many officers with pending vigilance inquiries have had their DPC promotions placed in sealed cover?",
      "compare_or_so_what", "ANSWERABLE", "SQL",
      "SELECT dpc_status, delay_bottleneck_reason, COUNT(*) as count_cases FROM hrfin_gold.mart_promotions_dpc WHERE vigilance_cleared = FALSE GROUP BY 1, 2")

# Q24: Crude oil sales to refineries and payment performance
add_p(24, "CMD", 1, "Which oil marketing companies (OMCs) and private refiners bought the most domestic crude from ONGC in FY26?",
      "primary (commercial_sales)", "ANSWERABLE", "SQL",
      "SELECT customer_id, entity_name, ROUND(SUM(oil_revenue_inr_cr), 2) as revenue_cr FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND oil_revenue_inr_cr > 0 GROUP BY 1, 2 ORDER BY revenue_cr DESC LIMIT 5")
add_p(24, "CMD", 2, "What was our coastal crude tanker demurrage penalty paid during coastal evacuation in FY26?",
      "marine_logistics", "GAP", "NONE",
      "", "Marine tanker charter voyage demurrage ledger is not present in the current operational dataset.")
add_p(24, "CMD", 3, "What is the outstanding trade receivables balance and aging distribution across our oil marketing customers?",
      "compare_or_so_what", "ANSWERABLE", "SQL",
      "SELECT customer_id, aging_bucket, is_disputed, ROUND(SUM(outstanding_amount_inr_cr), 2) as total_outstanding_cr FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND outstanding_amount_inr_cr IS NOT NULL GROUP BY 1, 2, 3 ORDER BY total_outstanding_cr DESC LIMIT 5")

# Q25: Parliament questions monitoring
add_p(25, "CMD", 1, "How many Parliament questions were handled across government departments in FY26, and what was their status?",
      "primary (parliament)", "ANSWERABLE", "SQL",
      "SELECT authority_or_department, current_status, COUNT(*) as pq_count FROM hrfin_gold.mart_governance_audit WHERE record_type = 'parliament_question' GROUP BY 1, 2")
add_p(25, "CMD", 2, "Were any Lok Sabha or Rajya Sabha questions raised specifically about contract labour, accidents, or safety?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT reference_number, subject_title, current_status FROM hrfin_gold.mart_governance_audit WHERE record_type = 'parliament_question' AND (LOWER(subject_title) LIKE '%accident%' OR LOWER(subject_title) LIKE '%safety%' OR LOWER(subject_title) LIKE '%contract%' OR LOWER(subject_title) LIKE '%blowout%') LIMIT 5")
add_p(25, "CMD", 3, "What is the standard operating timeline for corporate coordination to reply to starred Parliament questions?",
      "policy_procedure", "PARTIAL", "SEARCH",
      "standard timeline and procedure for replying to Lok Sabha starred questions in ONGC coordination cell",
      "Internal 48-hour inter-directorate coordination SOP workflow manual is not checked into the policy repository.")

# =========================================================================
# DIRECTOR (HR) (Q26 to Q37) -> 36 prompts
# =========================================================================

# Q26: Medical reimbursements indoor hospitalization
add_p(26, "Director (HR)", 1, "What was the total expenditure on medical claims in FY26, and what percentage went to empanelled hospitals?",
      "primary (welfare)", "ANSWERABLE", "SQL",
      "SELECT is_empanelled_hospital, COUNT(DISTINCT claim_id) as claims_count, ROUND(SUM(claimed_amount_inr)/10000000, 2) as claimed_cr, ROUND(SUM(approved_amount_inr)/10000000, 2) as approved_cr FROM hrfin_gold.mart_payroll_benefits WHERE fiscal_year = 'FY26' AND claim_id IS NOT NULL GROUP BY 1")
add_p(26, "Director (HR)", 2, "Which private hospital chains received the largest share of indoor medical reimbursement in FY26?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT hospital_name, is_empanelled_hospital, COUNT(DISTINCT claim_id) as claims_count, ROUND(SUM(approved_amount_inr)/10000000, 2) as approved_cr FROM hrfin_gold.mart_payroll_benefits WHERE fiscal_year = 'FY26' AND hospital_name IS NOT NULL GROUP BY 1, 2 ORDER BY approved_cr DESC LIMIT 5")
add_p(26, "Director (HR)", 3, "Under ONGC Medical Rules, what is the ceiling and approval authority for emergency treatment taken at non-empanelled hospitals?",
      "policy_search", "ANSWERABLE", "SEARCH",
      "what is the medical reimbursement limit for indoor hospital treatment for retired employees or non empanelled")

# Q27: Training / BOSIET / Safety certifications
add_p(27, "Director (HR)", 1, "How many training records and training hours were logged across our training institutes in FY26?",
      "primary (training)", "ANSWERABLE", "SQL",
      "SELECT institute, COUNT(DISTINCT training_record_id) as total_trainings, ROUND(SUM(training_hours), 0) as total_training_hours FROM hrfin_gold.mart_training_development WHERE fiscal_year = 'FY26' GROUP BY 1 ORDER BY total_training_hours DESC")
add_p(27, "Director (HR)", 2, "How many executives were nominated and completed offshore safety and leadership programmes in FY26?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT programme_name, completion_status, COUNT(*) as participants FROM hrfin_gold.mart_training_development WHERE fiscal_year = 'FY26' AND (programme_name LIKE '%Safety%' OR programme_name LIKE '%Leadership%' OR programme_name LIKE '%Offshore%') GROUP BY 1, 2 LIMIT 5")
add_p(27, "Director (HR)", 3, "What is the validity period of BOSIET / FOET offshore survival certification before mandatory refresher training?",
      "policy_standards", "PARTIAL", "SEARCH",
      "offshore survival safety training certificate validity BOSIET refresher OPITO standards",
      "OPITO standard 4-year validity guideline is referenced in technical circulars but not as a stand-alone policy rulebook.")

# Q28: Domicile mismatch in Assam Asset
add_p(28, "Director (HR)", 1, "In Assam Asset (Sivasagar/Nazira), how many regular employees are domiciled in Assam versus other states?",
      "primary (domicile)", "ANSWERABLE", "SQL",
      "SELECT CASE WHEN home_state_code = 'AS' THEN 'Domiciled in Assam' ELSE 'Non-Domicile' END as domicile_status, cadre, COUNT(*) as emp_count FROM hrfin_gold.mart_workforce WHERE wc_name LIKE '%Assam%' OR wc_name LIKE '%Nazira%' GROUP BY 1, 2 ORDER BY 2, 1")
add_p(28, "Director (HR)", 2, "What is the domicile ratio for executive versus non-executive staff in North-East work centres?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT cadre, SUM(CASE WHEN home_state_code = 'AS' THEN 1 ELSE 0 END) as assam_domicile, COUNT(*) as total_staff, ROUND(SUM(CASE WHEN home_state_code = 'AS' THEN 1 ELSE 0 END)/COUNT(*)*100, 1) as domicile_pct FROM hrfin_gold.mart_workforce WHERE hard_station_cat IN ('Category C', 'Hard Station') GROUP BY 1")
add_p(28, "Director (HR)", 3, "Has the Parliamentary Committee on Welfare of SC/ST or local forums raised queries regarding local employment in Assam?",
      "compare_parliament", "ANSWERABLE", "SQL",
      "SELECT reference_number, subject_title FROM hrfin_gold.mart_governance_audit WHERE record_type = 'parliament_question' AND LOWER(subject_title) LIKE '%assam%' LIMIT 3")

# Q29: Apprentices engagement under Apprentices Act
add_p(29, "Director (HR)", 1, "How many apprentices and trainees were engaged across ONGC work centres in FY26, and in which states?",
      "primary (apprentices)", "ANSWERABLE", "SQL",
      "SELECT state, COUNT(DISTINCT contract_id) as contracts, SUM(headcount) as apprentice_count FROM hrfin_gold.mart_contract_workforce WHERE service_category LIKE '%Apprentice%' OR service_category LIKE '%Trainee%' GROUP BY 1 ORDER BY apprentice_count DESC")
add_p(29, "Director (HR)", 2, "What is the trade-wise engagement of apprentices in technical vs non-technical trades?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT service_category, is_core_activity, SUM(headcount) as trainees_count, ROUND(SUM(monthly_cost_inr)/10000000, 2) as spend_cr FROM hrfin_gold.mart_contract_workforce WHERE service_category LIKE '%Apprentice%' OR service_category LIKE '%Support%' GROUP BY 1, 2")
add_p(29, "Director (HR)", 3, "What is the monthly stipend entitlement and NAPS subsidy reimbursement policy for trade apprentices?",
      "policy_stipend", "PARTIAL", "SEARCH",
      "trade apprentice monthly stipend reimbursement under National Apprenticeship Promotion Scheme NAPS",
      "NAPS portal direct benefit transfer transaction ledger is not maintained in the corporate data bank.")

# Q30: Leave encashment liability and balances
add_p(30, "Director (HR)", 1, "What was the total leave encashment expenditure disbursed to employees in FY26, and how many days were encashed?",
      "primary (leave_liability)", "ANSWERABLE", "SQL",
      "SELECT leave_type, COUNT(DISTINCT emp_id) as employees_count, ROUND(AVG(closing_balance_days), 1) as avg_closing_balance, ROUND(AVG(encashable_balance_days), 1) as avg_encashable_days FROM hrfin_gold.mart_payroll_benefits WHERE fiscal_year = 'FY26' AND leave_type IS NOT NULL GROUP BY 1")
add_p(30, "Director (HR)", 2, "How many executives currently hold an accumulated earned leave balance exceeding 250 days?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT cadre, COUNT(DISTINCT emp_id) as officers_over_250_days FROM hrfin_gold.mart_payroll_benefits WHERE fiscal_year = 'FY26' AND leave_type = 'Earned Leave' AND encashable_balance_days >= 250 GROUP BY 1")
add_p(30, "Director (HR)", 3, "What are the rules governing earned leave accumulation limit (300 days) and encashment upon superannuation?",
      "policy_search", "ANSWERABLE", "SEARCH",
      "how many days of earned leave do employees accumulate each year and what is the maximum balance")

# Q31: DPC promotions notification bottleneck
add_p(31, "Director (HR)", 1, "How many DPC promotion cases are currently pending notification, and what are the recorded bottleneck reasons?",
      "primary (promotions)", "ANSWERABLE", "SQL",
      "SELECT delay_bottleneck_reason, COUNT(*) as pending_count, ROUND(AVG(delay_months), 1) as avg_delay_months FROM hrfin_gold.mart_promotions_dpc WHERE dpc_status = 'Pending' GROUP BY 1 ORDER BY pending_count DESC")
add_p(31, "Director (HR)", 2, "In which executive grade transitions (e.g. E4 to E5, E5 to E6) is the promotion backlog highest?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT from_grade_id, to_grade_id, COUNT(*) as cases_count FROM hrfin_gold.mart_promotions_dpc WHERE dpc_status = 'Pending' GROUP BY 1, 2 ORDER BY cases_count DESC")
add_p(31, "Director (HR)", 3, "What are the minimum qualifying marks and APAR benchmarks required for merit promotion to Chief Manager (E5)?",
      "policy_search", "ANSWERABLE", "SEARCH",
      "what are the eligibility benchmarks and marks required in performance appraisal for merit promotion")

# Q32: Compassionate appointments and deceased employee cases
add_p(32, "Director (HR)", 1, "How many employees currently in service joined through compassionate appointment mode across grades?",
      "primary (welfare_compassionate)", "ANSWERABLE", "SQL",
      "SELECT current_grade_id, cadre, COUNT(*) as count_compassionate_recruits FROM hrfin_gold.mart_workforce WHERE entry_mode = 'Compassionate' GROUP BY 1, 2 ORDER BY 1")
add_p(32, "Director (HR)", 2, "How many separations due to death in service occurred during FY26 requiring family assistance?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT separation_type, COUNT(*) as separation_count FROM hrfin_silver.separations WHERE fiscal_year = 'FY26' GROUP BY 1")
add_p(32, "Director (HR)", 3, "What are the family pension and immediate ex-gratia relief provisions under ONGC Death-in-Service rules?",
      "policy_pension", "PARTIAL", "SEARCH",
      "family pension ex-gratia relief scheme for dependents of deceased employees ONGC rules",
      "Detailed Trust Deed of Composite Social Security Scheme (CSSS) for fatal accidental relief is not indexed in full.")

# Q33: Internal Complaints Committee (ICC) / POSH compliance
add_p(33, "Director (HR)", 1, "How many work centres have established Internal Complaints Committees (ICC) under the POSH Act, and are they active?",
      "primary (posh_compliance)", "ANSWERABLE", "SQL",
      "SELECT wc_name, presiding_officer_name, external_member_ngo, women_members_pct FROM hrfin_silver.icc_committees LIMIT 5")
add_p(33, "Director (HR)", 2, "How many POSH complaints were investigated enterprise-wide in FY26, and what was their status?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT case_type, status, COUNT(*) as total_cases FROM hrfin_gold.mart_employee_relations WHERE case_type = 'POSH' GROUP BY 1, 2")
add_p(33, "Director (HR)", 3, "Under ONGC POSH guidelines, what is the mandatory percentage of women members on each work centre ICC?",
      "policy_search", "ANSWERABLE", "SEARCH",
      "where to submit complaints regarding sexual harassment in the workplace")

# Q34: Sports and athlete welfare sponsorship
add_p(34, "Director (HR)", 1, "What was our total budget and spend under Sports Welfare and employee recreational programmes in FY26?",
      "primary (sports_welfare)", "PARTIAL", "SQL",
      "SELECT csr_theme, ROUND(SUM(actual_disbursed_inr_cr), 2) as spend_cr FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND LOWER(csr_theme) LIKE '%sport%' GROUP BY 1",
      "Direct non-CSR internal establishment budget for sports scholarships and sports quota DA is aggregated in general staff welfare.")
add_p(34, "Director (HR)", 2, "How many international and national medal-winning sportspersons are on ONGC's rolls by grade?",
      "sports_roster", "GAP", "NONE",
      "", "Roster of dedicated sports quota athletes and international tournament achievements is not maintained in silver HR tables.")
add_p(34, "Director (HR)", 3, "What is the entitlement for Special Casual Leave (SCL) granted to employees representing the organization in sports meets?",
      "policy_leave", "ANSWERABLE", "SEARCH",
      "can casual leave be combined with earned leave or study leave")

# Q35: Absenteeism and disciplinary penalties
add_p(35, "Director (HR)", 1, "Which work centres reported the highest incidence of disciplinary inquiries and chargesheets under CDA rules in FY26?",
      "primary (disciplinary)", "ANSWERABLE", "SQL",
      "SELECT wc_name, COUNT(*) as total_disciplinary_cases, SUM(CASE WHEN is_aged_over_3_years THEN 1 ELSE 0 END) as aged_over_3yr FROM hrfin_gold.mart_employee_relations WHERE case_type = 'Disciplinary' GROUP BY 1 ORDER BY total_disciplinary_cases DESC LIMIT 5")
add_p(35, "Director (HR)", 2, "What major penalties (reduction in rank, dismissal, withholding of increment) were awarded in FY26?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT status, COUNT(*) as cases_count FROM hrfin_gold.mart_employee_relations WHERE case_type = 'Disciplinary' GROUP BY 1")
add_p(35, "Director (HR)", 3, "Under ONGC CDA Rules, what is the formal procedure before awarding a major penalty of removal from service?",
      "policy_search", "ANSWERABLE", "SEARCH",
      "what are the rules governing disciplinary proceedings and minor penalty under conduct rules")

# Q36: Graduate Executive Trainee (GET) recruitment through GATE
add_p(36, "Director (HR)", 1, "How many Graduate Executive Trainees (GETs) joined ONGC through GATE in recent recruitment batches by discipline?",
      "primary (recruitment)", "ANSWERABLE", "SQL",
      "SELECT discipline_name, COUNT(*) as gets_count FROM hrfin_gold.mart_workforce WHERE entry_mode = 'GATE' GROUP BY 1 ORDER BY gets_count DESC LIMIT 5")
add_p(36, "Director (HR)", 2, "What was the social category breakup (SC, ST, OBC, EWS, UR) among newly recruited executive trainees?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT category, COUNT(*) as trainees_count, ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(), 1) as pct FROM hrfin_gold.mart_workforce WHERE entry_mode = 'GATE' GROUP BY 1")
add_p(36, "Director (HR)", 3, "What is the 3-year service bond amount and probation confirmation criteria for newly joined Graduate Executive Trainees?",
      "policy_service_bond", "PARTIAL", "SEARCH",
      "service bond amount and probation confirmation criteria for Graduate Executive Trainees GATE",
      "Specific executable indemnity bond deed format for new graduate trainees is not indexed in public policy rulebooks.")

# Q37: Service litigation before CAT and High Courts
add_p(37, "Director (HR)", 1, "How many service litigation cases are currently active across Central Administrative Tribunal (CAT) and High Courts?",
      "primary (litigation)", "ANSWERABLE", "SQL",
      "SELECT forum, COUNT(*) as active_cases, SUM(CASE WHEN interim_stay_granted THEN 1 ELSE 0 END) as stay_granted_cases FROM hrfin_gold.mart_employee_relations WHERE status = 'Active' GROUP BY 1 ORDER BY active_cases DESC")
add_p(37, "Director (HR)", 2, "In how many active court cases has an interim stay order been granted against transfers or promotion orders?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT case_category, COUNT(*) as stayed_cases FROM hrfin_gold.mart_employee_relations WHERE interim_stay_granted = TRUE GROUP BY 1")
add_p(37, "Director (HR)", 3, "What was our total expenditure on legal retainer fees and senior advocate appearances in FY26?",
      "legal_expenses", "GAP", "NONE",
      "", "External legal counsel fee vouchers and advocate retainer ledgers are not segregated from general administrative expenses.")

# =========================================================================
# DIRECTOR (FINANCE) (Q38 to Q50) -> 39 prompts
# =========================================================================

# Q38: Procurement 25% MSE compliance target
add_p(38, "Director (Finance)", 1, "Did ONGC achieve the mandatory 25% procurement target from Micro and Small Enterprises (MSEs) in FY26?",
      "primary (mse_compliance)", "ANSWERABLE", "SQL",
      "SELECT is_mse_vendor, COUNT(DISTINCT po_number) as pos_count, ROUND(SUM(actual_paid_amount_inr)/10000000, 2) as spend_cr, ROUND(SUM(actual_paid_amount_inr)/SUM(SUM(actual_paid_amount_inr)) OVER() * 100, 1) as spend_pct FROM hrfin_gold.mart_procurement_contracts WHERE fiscal_year = 'FY26' GROUP BY 1")
add_p(38, "Director (Finance)", 2, "What was the procurement spend share directed to SC/ST-owned and Women-owned MSE enterprises in FY26?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT vendor_category, is_mse_vendor, COUNT(DISTINCT vendor_id) as vendors, ROUND(SUM(actual_paid_amount_inr)/10000000, 2) as spend_cr FROM hrfin_gold.mart_procurement_contracts WHERE fiscal_year = 'FY26' AND is_mse_vendor = TRUE GROUP BY 1, 2")
add_p(38, "Director (Finance)", 3, "Under DPE / Public Procurement Policy, what reporting to the Ministry of MSME is mandated if a CPSE misses the 25% target?",
      "policy_msme", "PARTIAL", "SEARCH",
      "Public Procurement Policy for MSEs Order 2012 non compliance reporting to Ministry of MSME",
      "Annual MSME Sambandh portal filing confirmation receipt is not archived in the local document repository.")

# Q39: Government e-Marketplace (GeM) spend share
add_p(39, "Director (Finance)", 1, "What percentage of our procurement contracts and purchase orders was executed through the GeM portal in FY26?",
      "primary (gem_procurement)", "ANSWERABLE", "SQL",
      "SELECT vendor_category, COUNT(DISTINCT po_number) as pos, ROUND(SUM(actual_paid_amount_inr)/10000000, 2) as spend_cr FROM hrfin_gold.mart_procurement_contracts WHERE fiscal_year = 'FY26' GROUP BY 1 ORDER BY spend_cr DESC")
add_p(39, "Director (Finance)", 2, "Which work centres have the highest procurement spend through MSE and local vendors?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT wc_name, ROUND(SUM(actual_paid_amount_inr)/10000000, 2) as total_spend_cr, ROUND(SUM(CASE WHEN is_mse_vendor THEN actual_paid_amount_inr ELSE 0 END)/10000000, 2) as mse_spend_cr FROM hrfin_gold.mart_procurement_contracts WHERE fiscal_year = 'FY26' GROUP BY 1 ORDER BY total_spend_cr DESC LIMIT 5")
add_p(39, "Director (Finance)", 3, "Are specialized high-value offshore drilling and well stimulation services exempted from mandatory GeM buying?",
      "policy_search", "ANSWERABLE", "SEARCH",
      "guidelines for procurement of goods and services through GeM exemptions for oilfield services")

# Q40: Working Capital / Debtor Days (DSO)
add_p(40, "Director (Finance)", 1, "What is our trade receivables position as of 31 March 2026, and which customers account for the bulk of outstanding dues?",
      "primary (working_capital)", "ANSWERABLE", "SQL",
      "SELECT customer_id, aging_bucket, is_disputed, ROUND(SUM(outstanding_amount_inr_cr), 2) as outstanding_cr FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND outstanding_amount_inr_cr IS NOT NULL GROUP BY 1, 2, 3 ORDER BY outstanding_cr DESC LIMIT 5")
add_p(40, "Director (Finance)", 2, "How much in receivables has been aging for more than 90 days across power and fertilizer customers?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT aging_bucket, COUNT(*) as invoices_count, ROUND(SUM(outstanding_amount_inr_cr), 2) as amount_cr FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND aging_days > 90 GROUP BY 1")
add_p(40, "Director (Finance)", 3, "What is the provision for doubtful debts and expected credit loss (ECL) under Ind AS 109 on disputed receivables?",
      "accounting_standard", "ANSWERABLE", "SQL",
      "SELECT is_disputed, dispute_reason, ROUND(SUM(outstanding_amount_inr_cr), 2) as disputed_cr FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND is_disputed = TRUE GROUP BY 1, 2")

# Q41: Statutory Levies / Windfall Tax (SAED)
add_p(41, "Director (Finance)", 1, "How much total Special Additional Excise Duty (SAED / windfall tax), OIDB Cess, and Royalty did ONGC pay in FY26?",
      "primary (statutory_levies)", "ANSWERABLE", "SQL",
      "SELECT fiscal_year, ROUND(royalty_inr_cr, 2) as royalty_cr, ROUND(oidb_cess_inr_cr, 2) as cess_cr, ROUND(saed_windfall_tax_inr_cr, 2) as windfall_tax_cr, ROUND(statutory_levies_total_inr_cr, 2) as total_levies_cr FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND gross_revenue_inr_cr IS NOT NULL LIMIT 1")
add_p(41, "Director (Finance)", 2, "What was the deduction per barrel of crude oil on account of statutory levies in FY26?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT fiscal_year, ongc_crude_net_realisation_usd_bbl, cess_per_barrel_usd, royalty_per_barrel_usd, windfall_tax_saed_usd_bbl FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND ongc_crude_net_realisation_usd_bbl IS NOT NULL LIMIT 1")
add_p(41, "Director (Finance)", 3, "What was the total net statutory levies reduction across individual producing assets in FY26?",
      "compare_or_so_what", "ANSWERABLE", "SQL",
      "SELECT asset_name, ROUND(SUM(statutory_royalty_inr_cr), 2) as royalty_cr, ROUND(SUM(statutory_cess_inr_cr), 2) as cess_cr, ROUND(SUM(statutory_windfall_tax_saed_inr_cr), 2) as windfall_cr FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' GROUP BY 1 ORDER BY (royalty_cr + cess_cr + windfall_cr) DESC LIMIT 5")

# Q42: Asset-wise P&L / EBITDA Margin Analysis
add_p(42, "Director (Finance)", 1, "What was the operating profit margin (EBITDA margin %) of Western Offshore versus Onshore producing assets in FY26?",
      "primary (pnl_margin)", "ANSWERABLE", "SQL",
      "SELECT onshore_offshore, ROUND(SUM(gross_revenue_inr_cr), 2) as rev_cr, ROUND(SUM(total_opex_inr_cr), 2) as opex_cr, ROUND(SUM(ebitda_inr_cr), 2) as ebitda_cr, ROUND(SUM(ebitda_inr_cr)/NULLIF(SUM(gross_revenue_inr_cr),0)*100, 1) as ebitda_margin_pct FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' GROUP BY 1")
add_p(42, "Director (Finance)", 2, "Among all onshore assets, which asset had the lowest EBITDA margin in FY26 and why?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT asset_name, ROUND(SUM(gross_revenue_inr_cr), 2) as rev_cr, ROUND(SUM(total_opex_inr_cr), 2) as opex_cr, ROUND(SUM(ebitda_inr_cr), 2) as ebitda_cr, ROUND(SUM(ebitda_inr_cr)/NULLIF(SUM(gross_revenue_inr_cr),0)*100, 1) as margin_pct FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' AND onshore_offshore = 'Onshore' GROUP BY 1 ORDER BY margin_pct ASC LIMIT 5")
add_p(42, "Director (Finance)", 3, "What were the three largest operating expense heads in Assam Asset that contributed to high lifting cost?",
      "compare_or_so_what", "ANSWERABLE", "SQL",
      "SELECT asset_name, ROUND(SUM(allocated_manpower_cost_inr_cr), 2) as manpower_cost_cr, ROUND(SUM(workover_repairs_cost_inr_cr), 2) as workover_cr, ROUND(SUM(power_fuel_cost_inr_cr), 2) as power_cost_cr, ROUND(SUM(total_opex_inr_cr), 2) as total_opex_cr FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' AND asset_name = 'Assam Asset' GROUP BY 1")

# Q43: Corporate cash, deposits & treasury yield
add_p(43, "Director (Finance)", 1, "What was our standalone Return on Capital Employed (ROCE) and Profit After Tax (PAT) in FY26 vs FY25?",
      "primary (treasury)", "ANSWERABLE", "SQL",
      "SELECT fiscal_year, gross_revenue_inr_cr, pat_inr_cr, standalone_roce_pct, consolidated_pat_inr_cr FROM hrfin_gold.mart_corporate_performance WHERE gross_revenue_inr_cr IS NOT NULL ORDER BY fiscal_year")
add_p(43, "Director (Finance)", 2, "What was the total employee benefit expense relative to gross revenue in FY26?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT fiscal_year, employee_cost_total_inr_cr, gross_revenue_inr_cr, ROUND(employee_cost_total_inr_cr / NULLIF(gross_revenue_inr_cr, 0) * 100, 2) as emp_cost_pct_rev FROM hrfin_gold.mart_corporate_performance WHERE gross_revenue_inr_cr IS NOT NULL ORDER BY fiscal_year")
add_p(43, "Director (Finance)", 3, "What is the breakdown of bank term deposit accounts by individual public sector bank branch?",
      "bank_deposits_ledger", "GAP", "NONE",
      "", "Granular bank account statement balances per individual bank branch are not stored in the silver financial warehouse.")

# Q44: Foreign exchange hedging strategy
add_p(44, "Director (Finance)", 1, "What is the total open foreign exchange exposure on dollar-linked EPC and drilling contracts in FY26?",
      "primary (forex)", "ANSWERABLE", "SQL",
      "SELECT underlying_contract_category, COUNT(*) as contracts, ROUND(SUM(gross_exposure_usd)/1000000, 2) as gross_usd_m, ROUND(SUM(hedged_amount_usd)/1000000, 2) as hedged_usd_m, ROUND(SUM(unhedged_exposure_usd)/1000000, 2) as unhedged_usd_m FROM hrfin_silver.forex_hedges WHERE fiscal_year = 'FY26' GROUP BY 1")
add_p(44, "Director (Finance)", 2, "What derivative instruments (forward contracts, currency swaps) are currently deployed under our hedging policy?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT currency_pair, ROUND(SUM(hedged_amount_usd)/1000000, 2) as hedged_m_usd, ROUND(AVG(hedge_ratio_pct), 1) as avg_hedge_pct FROM hrfin_silver.forex_hedges WHERE fiscal_year = 'FY26' GROUP BY 1")
add_p(44, "Director (Finance)", 3, "What are the Board-approved treasury limits on derivative contracts under ONGC Risk Management Policy?",
      "policy_risk", "PARTIAL", "SEARCH",
      "foreign exchange risk management policy hedging limit derivative forward contracts",
      "Treasury Committee operational limits on derivative counterparties are documented in confidential treasury manuals.")

# Q45: DDA & dry well write-offs
add_p(45, "Director (Finance)", 1, "What was our total Depletion, Depreciation, and Amortisation (DDA) expense in FY26 and how has it trended?",
      "primary (dda)", "ANSWERABLE", "SQL",
      "SELECT fiscal_year, dda_inr_cr, gross_revenue_inr_cr, ROUND(dda_inr_cr / NULLIF(gross_revenue_inr_cr, 0) * 100, 1) as dda_pct_revenue FROM hrfin_gold.mart_corporate_performance WHERE gross_revenue_inr_cr IS NOT NULL ORDER BY fiscal_year")
add_p(45, "Director (Finance)", 2, "What was the total exploratory drilling cost written off to dry wells in FY26?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT result_status, COUNT(*) as wells_count, ROUND(SUM(drilling_cost_inr_cr), 2) as total_drilling_cost_cr FROM hrfin_gold.mart_production_reserves WHERE fiscal_year = 'FY26' AND well_type = 'Exploratory' GROUP BY 1")
add_p(45, "Director (Finance)", 3, "Under Ind AS 106 and Successful Efforts Method, how is DDA accounted for exploratory discoveries?",
      "accounting_glossary", "ANSWERABLE", "SQL",
      "SELECT term, full_form, definition FROM hrfin_gold.glossary WHERE term = 'DDA'")

# Q46: Capital Work in Progress (CWIP) and capex burn rate
add_p(46, "Director (Finance)", 1, "What was our total capex budget utilisation across major project heads in FY26?",
      "primary (cwip)", "ANSWERABLE", "SQL",
      "SELECT capex_head, ROUND(SUM(budget_estimate_be_inr_cr), 2) as be_cr, ROUND(SUM(revised_estimate_re_inr_cr), 2) as re_cr, ROUND(SUM(actual_spend_inr_cr), 2) as actual_cr, ROUND(SUM(actual_spend_inr_cr)/NULLIF(SUM(revised_estimate_re_inr_cr), 0)*100, 1) as util_pct FROM hrfin_gold.mart_capex_projects WHERE fiscal_year = 'FY26' GROUP BY 1 ORDER BY actual_cr DESC")
add_p(46, "Director (Finance)", 2, "Which projects are experiencing cost overruns exceeding 15% of sanctioned cost?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT project_name, sanctioned_cost_inr_cr, actual_spend_inr_cr, cost_overrun_inr_cr, cost_overrun_pct FROM hrfin_gold.mart_capex_projects WHERE fiscal_year = 'FY26' AND cost_overrun_pct > 15 ORDER BY cost_overrun_pct DESC LIMIT 5")
add_p(46, "Director (Finance)", 3, "What are the primary delay root causes identified for delayed capital projects?",
      "compare_or_so_what", "ANSWERABLE", "SQL",
      "SELECT delay_root_cause_category, COUNT(DISTINCT prj_id) as delayed_projects, ROUND(SUM(cost_overrun_inr_cr), 2) as total_overrun_cr FROM hrfin_gold.mart_capex_projects WHERE fiscal_year = 'FY26' AND delay_root_cause_category IS NOT NULL GROUP BY 1 ORDER BY delayed_projects DESC")

# Q47: Gas transmission charges and pipeline handling
add_p(47, "Director (Finance)", 1, "What was the total logistics and transport handling cost incurred across producing assets in FY26?",
      "primary (gas_tariffs)", "ANSWERABLE", "SQL",
      "SELECT onshore_offshore, ROUND(SUM(logistics_osv_chopper_cost_inr_cr), 2) as logistics_cost_cr, ROUND(SUM(total_opex_inr_cr), 2) as total_opex_cr FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' GROUP BY 1")
add_p(47, "Director (Finance)", 2, "Which offshore assets incurred the highest offshore support vessel (OSV) and helicopter logistics spend?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT asset_name, ROUND(SUM(logistics_osv_chopper_cost_inr_cr), 2) as logistics_cr FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' AND onshore_offshore = 'Offshore' GROUP BY 1 ORDER BY logistics_cr DESC")
add_p(47, "Director (Finance)", 3, "Did ONGC incur any ship-or-pay gas pipeline transmission penalties with GAIL during FY26?",
      "pipeline_penalties", "GAP", "NONE",
      "", "Bilateral Gas Transmission Agreement (GTA) penalty settlement invoices are not broken out into a distinct table.")

# Q48: Corporate guarantees and inter-corporate loans to subsidiaries
add_p(48, "Director (Finance)", 1, "What was the annual revenue and PAT contribution of all subsidiary and JV entities in FY26?",
      "primary (subsidiary_guarantees)", "ANSWERABLE", "SQL",
      "SELECT entity_name, ongc_equity_holding_pct, revenue_inr_cr, ebitda_inr_cr, pat_inr_cr FROM hrfin_silver.subsidiary_financials WHERE fiscal_year = 'FY26' ORDER BY revenue_inr_cr DESC")
add_p(48, "Director (Finance)", 2, "What was the dividend payout from international production through ONGC Videsh Limited (OVL)?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT entity_name, subsidiary_pat_inr_cr, dividend_received_by_ongc_inr_cr FROM hrfin_silver.subsidiary_financials WHERE entity_name LIKE '%Videsh%' AND fiscal_year = 'FY26'")
add_p(48, "Director (Finance)", 3, "What is our total outstanding parent company financial guarantee liability backing OVL international loans?",
      "contingent_liabilities", "PARTIAL", "SEARCH",
      "contingent liabilities corporate guarantees extended to subsidiaries note 43 financial statements",
      "Parent corporate guarantee schedules are described in Annual Report Note 43 text but lack a dedicated transactional ledger.")

# Q49: Cost control and power/fuel expenses
add_p(49, "Director (Finance)", 1, "What was the total power and fuel cost incurred across our producing assets in FY26?",
      "primary (cost_control)", "ANSWERABLE", "SQL",
      "SELECT onshore_offshore, ROUND(SUM(power_fuel_cost_inr_cr), 2) as power_cost_cr, ROUND(SUM(power_fuel_cost_inr_cr)/SUM(total_opex_inr_cr)*100, 1) as power_cost_pct_opex FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' GROUP BY 1")
add_p(49, "Director (Finance)", 2, "Which individual onshore fields consumed the highest power and fuel expenses?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT field_name, asset_name, ROUND(SUM(power_fuel_cost_inr_cr), 2) as power_cost_cr, ROUND(AVG(water_cut_pct), 1) as wc_pct FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' AND onshore_offshore = 'Onshore' GROUP BY 1, 2 ORDER BY power_cost_cr DESC LIMIT 5")
add_p(49, "Director (Finance)", 3, "What power tariff optimization and captive power plant generation targets were assigned for FY27?",
      "operational_targets", "GAP", "NONE",
      "", "Internal Asset Business Plan power consumption reduction targets are in annual budget dossiers not ingested into BigQuery.")

# Q50: Dividend payout vs DIPAM guidelines
add_p(50, "Director (Finance)", 1, "What was our total dividend payout and dividend payout ratio as a percentage of standalone PAT in FY26?",
      "primary (dividend_dipam)", "ANSWERABLE", "SQL",
      "SELECT fiscal_year, pat_inr_cr, dividend_per_share_inr, total_dividend_payout_inr_cr, dividend_payout_ratio_pct FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND pat_inr_cr IS NOT NULL LIMIT 1")
add_p(50, "Director (Finance)", 2, "What was the total dividend received by the Government of India as the majority shareholder in FY26?",
      "drill_down", "ANSWERABLE", "SQL",
      "SELECT fiscal_year, total_dividend_payout_inr_cr, ROUND(total_dividend_payout_inr_cr * 0.5889, 2) as goi_dividend_share_cr FROM hrfin_gold.mart_corporate_performance WHERE fiscal_year = 'FY26' AND total_dividend_payout_inr_cr IS NOT NULL LIMIT 1")
add_p(50, "Director (Finance)", 3, "What is the DIPAM capital restructuring guideline requirement on minimum dividend distribution for CPSEs?",
      "policy_search", "ANSWERABLE", "SEARCH",
      "what is the government directive regarding minimum dividend payout as percentage of profit after tax")

with open('verify/stress_test_prompts.json', 'w') as f:
    json.dump(prompts, f, indent=2)

print(f"Generated {len(prompts)} prompts across 50 questions!")
