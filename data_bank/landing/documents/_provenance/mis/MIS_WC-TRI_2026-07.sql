-- ============================================================================
-- Provenance SQL for Monthly Asset Performance Report (Step 3.4)
-- Asset Work Centre: WC-TRI
-- Reporting Month: 2026-07
-- Comparisons: Previous Month (2026-06), Same Month Last Year (2025-07)
-- ============================================================================

-- Query 1: Physical Hydrocarbon Production & Well Downtime
SELECT 
    month,
    COALESCE(SUM(oil_production_mt), 0.0) as oil_production_mt,
    COALESCE(SUM(gas_production_mmscm), 0.0) as gas_production_mmscm,
    COALESCE(SUM(condensate_production_mt), 0.0) as condensate_production_mt,
    COALESCE(SUM(total_production_boe), 0.0) as total_production_boe,
    COALESCE(AVG(water_cut_pct), 0.0) as water_cut_pct,
    COALESCE(SUM(water_produced_m3), 0.0) as water_produced_m3,
    COALESCE(SUM(active_producing_wells), 0) as active_producing_wells,
    COALESCE(SUM(well_downtime_hours), 0.0) as well_downtime_hours,
    COALESCE(AVG(operational_uptime_pct), 0.0) as operational_uptime_pct
FROM 'landing/db_exports/production_monthly.csv'
WHERE asset_wc_id = 'WC-TRI' AND month IN ('2026-07', '2026-06', '2025-07')
GROUP BY month
ORDER BY month;

-- Query 2: Operating Expenditure (OPEX) by Cost Head & Cost Element
SELECT 
    cost_head,
    cost_element_name,
    COALESCE(SUM(amount_inr), 0.0) as amount_inr
FROM 'landing/sap/COSP_COSS.csv'
WHERE wc_id = 'WC-TRI' AND month = '2026-07'
GROUP BY cost_head, cost_element_name
ORDER BY amount_inr DESC;

-- Query 3: Capital Expenditure (Capex Actual vs Budget Estimate BE)
SELECT 
    COALESCE(SUM(budget_estimate_be_inr_cr), 0.0) as be_inr_cr,
    COALESCE(SUM(revised_estimate_re_inr_cr), 0.0) as re_inr_cr,
    COALESCE(SUM(actual_spend_inr_cr), 0.0) as actual_spend_inr_cr,
    (COALESCE(SUM(actual_spend_inr_cr), 0.0) - COALESCE(SUM(budget_estimate_be_inr_cr), 0.0)) as variance_vs_be_cr
FROM capex_budget
WHERE asset_wc_id = 'WC-TRI' AND month = '2026-07';

-- Query 4: Manpower In-Position Headcount Snapshot
SELECT 
    COALESCE(SUM(headcount), 0) as total_headcount,
    COALESCE(SUM(active_headcount), 0) as active_headcount,
    COALESCE(SUM(on_leave_headcount), 0) as on_leave_headcount
FROM 'landing/sap/headcount_monthly_snapshot.csv'
WHERE wc_id = 'WC-TRI' AND month = '2026-07';

-- Query 5: Payroll Overtime Hours & Expenditure
SELECT 
    COALESCE(COUNT(DISTINCT PERNR), 0) as paid_employees,
    COALESCE(SUM(overtime_hours), 0.0) as total_overtime_hours,
    COALESCE(SUM(overtime_amount_inr), 0.0) as total_overtime_amount_inr
FROM 'landing/sap/PY_CLUSTER_EXP.csv'
WHERE wc_id = 'WC-TRI' AND FPPER = '2026-07';

-- Query 6: Health, Safety & Environment (HSE) Incidents
SELECT 
    COALESCE(COUNT(*), 0) as total_incidents,
    COALESCE(SUM(CASE WHEN lost_time_injury_flag = TRUE THEN 1 ELSE 0 END), 0) as lti_count,
    COALESCE(SUM(days_lost), 0) as total_days_lost,
    COALESCE(SUM(CASE WHEN fatigue_factor_flag = TRUE THEN 1 ELSE 0 END), 0) as fatigue_incidents
FROM 'landing/db_exports/hse_incident_log.csv'
WHERE wc_id = 'WC-TRI' AND month = '2026-07';
