"""Builds the 4 authoritative BigQuery Single Source of Truth (SSOT) 360° tables in `hrfin_gold`:
[DEPRECATED] This script is deprecated in v3. Use Dataform definitions instead.
"""

from google.cloud import bigquery
from app.config import BQ_LOCATION, GCP_PROJECT, JOB_LABELS


def main() -> None:
    print("DEPRECATED: Use Dataform v3 for ssot_employee_360 and ssot_workforce_employee. Exiting.")
    return
    client = bigquery.Client(
        project=GCP_PROJECT,
        location=BQ_LOCATION,
        default_query_job_config=bigquery.QueryJobConfig(labels=JOB_LABELS),
    )

    # 1. Build ssot_workforce_employee (exact 1 row per emp_id)
    q_ssot_emp = """
    CREATE OR REPLACE TABLE `ongc-hr-finance-agent.hrfin_gold.ssot_workforce_employee`
    CLUSTER BY current_wc_id, current_grade_id, discipline_id
    AS
    WITH cs AS (
      SELECT
        emp_id,
        ARRAY_AGG(STRUCT(continuous_from_date, continuous_stay_months, continuous_stay_years, is_continuous_5yr_plus, is_superannuation_exempt) ORDER BY continuous_stay_months DESC LIMIT 1)[OFFSET(0)] AS stay
      FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay`
      WHERE is_current_stay = TRUE
      GROUP BY emp_id
    ),
    ct AS (
      SELECT
        emp_id,
        ARRAY_AGG(STRUCT(cluster_id, cluster_name, cumulative_cluster_years, has_breached_cluster_10yr_cap) ORDER BY cumulative_cluster_years DESC LIMIT 1)[OFFSET(0)] AS cl
      FROM `ongc-hr-finance-agent.hrfin_gold.v_cluster_cumulative_tenure`
      WHERE is_currently_in_cluster = TRUE
      GROUP BY emp_id
    ),
    apar AS (
      SELECT
        emp_id,
        ARRAY_AGG(STRUCT(numerical_score, final_rating, is_dpc_eligible) ORDER BY fiscal_year DESC LIMIT 1)[OFFSET(0)] AS ap
      FROM `ongc-hr-finance-agent.hrfin_silver.apar_ratings`
      WHERE fiscal_year IN ("FY26", "2026")
      GROUP BY emp_id
    ),
    trn AS (
      SELECT
        emp_id,
        SUM(COALESCE(training_hours, 0)) AS fy26_training_hours,
        SUM(COALESCE(training_days, 0)) AS fy26_training_days,
        COUNT(DISTINCT programme_id) AS fy26_programmes_completed
      FROM `ongc-hr-finance-agent.hrfin_silver.training_records`
      WHERE fiscal_year IN ("FY26", "2026")
      GROUP BY emp_id
    ),
    pay AS (
      SELECT
        emp_id,
        SUM(COALESCE(gross_salary_inr, 0)) AS fy26_gross_salary_inr,
        SUM(COALESCE(basic_pay_inr, 0)) AS fy26_basic_pay_inr,
        SUM(COALESCE(overtime_hours, 0)) AS fy26_overtime_hours,
        SUM(COALESCE(overtime_amount_inr, 0)) AS fy26_overtime_amount_inr,
        SUM(COALESCE(prp_inr, 0)) AS fy26_prp_inr,
        AVG(COALESCE(gross_salary_inr, 0)) AS avg_monthly_gross_inr
      FROM `ongc-hr-finance-agent.hrfin_silver.payroll_monthly`
      WHERE fiscal_year IN ("FY26", "2026")
      GROUP BY emp_id
    ),
    lv AS (
      SELECT
        emp_id,
        MAX(IF(UPPER(leave_type) = "EL", closing_balance_days, NULL)) AS el_balance_days,
        MAX(IF(UPPER(leave_type) = "EL", encashable_balance_days, NULL)) AS el_encashable_days,
        MAX(IF(UPPER(leave_type) = "HPL", closing_balance_days, NULL)) AS hpl_balance_days
      FROM `ongc-hr-finance-agent.hrfin_silver.leave_ledger`
      WHERE fiscal_year IN ("FY26", "2026")
      GROUP BY emp_id
    )
    SELECT
      e.emp_id,
      e.name AS emp_name,
      e.name,
      e.gender,
      e.dob,
      e.doj,
      e.fiscal_year_joined,
      COALESCE(e.age_years, ROUND(DATE_DIFF(DATE "2026-10-19", e.dob, DAY) / 365.25, 1)) AS age_years,
      e.age_band,
      COALESCE(e.total_tenure_years, ROUND(DATE_DIFF(COALESCE(e.separation_date, DATE "2026-10-19"), e.doj, DAY) / 365.25, 1)) AS total_tenure_years,
      e.tenure_band,
      e.category AS social_category,
      e.category,
      e.pwd_flag,
      e.pwd_category,
      e.home_state_code,
      e.current_grade_id AS grade_id,
      e.current_grade_id,
      g.cadre,
      g.`group` AS group_class,
      g.designation AS grade_designation,
      g.level_order AS grade_level_order,
      e.discipline_id,
      d.code AS discipline_code,
      d.name AS discipline_name,
      d.function AS discipline_function,
      e.current_wc_id AS wc_id,
      e.current_wc_id,
      w.name AS wc_name,
      w.short_name AS wc_short_name,
      w.city,
      w.state,
      w.sector,
      w.cluster_id,
      COALESCE(ct.cl.cluster_name, w.cluster_id) AS cluster_name,
      w.hard_station_cat,
      w.onshore_offshore,
      w.type AS wc_type,
      w.is_corporate_hq,
      e.current_designation,
      e.entry_mode,
      e.employment_status,
      e.separation_date,
      e.retirement_date,
      ROUND(DATE_DIFF(e.retirement_date, DATE "2026-10-19", DAY) / 365.25, 2) AS years_to_retirement,
      DATE_DIFF(e.retirement_date, DATE "2026-10-19", DAY) BETWEEN 0 AND 1096 AS is_retiring_within_3yr,
      e.has_hard_station_tenure,
      e.has_offshore_tenure,
      e.exemption_tag,
      e.exemption_reason_code,
      COALESCE(cs.stay.continuous_from_date, e.doj) AS continuous_from_date,
      COALESCE(cs.stay.continuous_stay_months, 0) AS continuous_stay_months,
      COALESCE(cs.stay.continuous_stay_years, 0.0) AS continuous_stay_years,
      COALESCE(cs.stay.is_continuous_5yr_plus, FALSE) AS is_continuous_5yr_plus,
      COALESCE(cs.stay.is_superannuation_exempt, FALSE) AS is_superannuation_exempt,
      COALESCE(ct.cl.cumulative_cluster_years, 0.0) AS cumulative_cluster_years,
      COALESCE(ct.cl.has_breached_cluster_10yr_cap, FALSE) AS has_breached_cluster_10yr_cap,
      apar.ap.numerical_score AS fy26_apar_score,
      apar.ap.final_rating AS fy26_apar_rating,
      COALESCE(apar.ap.is_dpc_eligible, FALSE) AS is_dpc_eligible,
      COALESCE(trn.fy26_training_hours, 0) AS fy26_training_hours,
      COALESCE(trn.fy26_training_days, 0) AS fy26_training_days,
      COALESCE(trn.fy26_programmes_completed, 0) AS fy26_programmes_completed,
      COALESCE(pay.fy26_gross_salary_inr, 0) AS fy26_gross_salary_inr,
      ROUND(COALESCE(pay.fy26_gross_salary_inr, 0) / 100000.0, 2) AS fy26_gross_salary_lakh,
      COALESCE(pay.avg_monthly_gross_inr, 0) AS avg_monthly_gross_inr,
      COALESCE(pay.fy26_overtime_hours, 0) AS fy26_overtime_hours,
      COALESCE(pay.fy26_overtime_amount_inr, 0) AS fy26_overtime_amount_inr,
      COALESCE(pay.fy26_prp_inr, 0) AS fy26_prp_inr,
      COALESCE(lv.el_balance_days, 0) AS el_balance_days,
      COALESCE(lv.el_encashable_days, 0) AS el_encashable_days,
      COALESCE(lv.hpl_balance_days, 0) AS hpl_balance_days,
      IF(LOWER(e.employment_status) = "active", 1, 0) AS active_headcount,
      IF(LOWER(e.employment_status) = "active", 1, 0) AS in_position_strength
    FROM `ongc-hr-finance-agent.hrfin_silver.employee_master` e
    LEFT JOIN `ongc-hr-finance-agent.hrfin_silver.dim_work_centre` w ON e.current_wc_id = w.wc_id
    LEFT JOIN `ongc-hr-finance-agent.hrfin_silver.dim_grade` g ON e.current_grade_id = g.grade_id
    LEFT JOIN `ongc-hr-finance-agent.hrfin_silver.dim_discipline` d ON e.discipline_id = d.discipline_id
    LEFT JOIN cs ON e.emp_id = cs.emp_id
    LEFT JOIN ct ON e.emp_id = ct.emp_id
    LEFT JOIN apar ON e.emp_id = apar.emp_id
    LEFT JOIN trn ON e.emp_id = trn.emp_id
    LEFT JOIN pay ON e.emp_id = pay.emp_id
    LEFT JOIN lv ON e.emp_id = lv.emp_id
    """
    client.query(q_ssot_emp).result()
    print("[1/4] Created hrfin_gold.ssot_workforce_employee")

    # 2. Build ssot_work_centre_360 (1 row per wc_id)
    q_ssot_wc = """
    CREATE OR REPLACE TABLE `ongc-hr-finance-agent.hrfin_gold.ssot_work_centre_360`
    CLUSTER BY wc_id, state, onshore_offshore
    AS
    WITH emp AS (
      SELECT
        wc_id,
        SUM(active_headcount) AS active_headcount,
        COUNTIF(active_headcount = 1 AND LOWER(cadre) = "executive") AS executive_headcount,
        COUNTIF(active_headcount = 1 AND LOWER(cadre) != "executive") AS non_executive_headcount,
        COUNTIF(active_headcount = 1 AND UPPER(gender) = "F") AS women_headcount,
        ROUND(SAFE_DIVIDE(COUNTIF(active_headcount = 1 AND UPPER(gender) = "F") * 100.0, NULLIF(SUM(active_headcount), 0)), 2) AS women_pct,
        COUNTIF(active_headcount = 1 AND UPPER(social_category) = "SC") AS sc_headcount,
        COUNTIF(active_headcount = 1 AND UPPER(social_category) = "ST") AS st_headcount,
        COUNTIF(active_headcount = 1 AND UPPER(social_category) = "OBC") AS obc_headcount,
        COUNTIF(active_headcount = 1 AND pwd_flag = TRUE) AS pwd_headcount,
        ROUND(AVG(IF(active_headcount = 1, age_years, NULL)), 1) AS avg_age_years,
        ROUND(AVG(IF(active_headcount = 1, total_tenure_years, NULL)), 1) AS avg_tenure_years,
        COUNTIF(active_headcount = 1 AND is_retiring_within_3yr = TRUE) AS retiring_within_3yr_count,
        COUNTIF(active_headcount = 1 AND LOWER(cadre) = "executive" AND continuous_stay_months >= 60) AS continuous_stay_5yr_plus_execs,
        COUNTIF(active_headcount = 1 AND LOWER(cadre) = "executive" AND continuous_stay_months >= 60 AND is_superannuation_exempt = FALSE) AS due_for_transfer_execs,
        ROUND(SUM(fy26_gross_salary_inr) / 10000000.0, 2) AS payroll_gross_inr_cr_fy26,
        ROUND(SUM(fy26_overtime_hours), 0) AS overtime_hours_fy26,
        ROUND(SUM(fy26_overtime_amount_inr) / 10000000.0, 2) AS overtime_cost_inr_cr_fy26,
        ROUND(SUM(fy26_training_hours), 0) AS training_hours_fy26,
        COUNTIF(fy26_training_hours > 0) AS trained_employees_fy26,
        ROUND(AVG(IF(active_headcount = 1, fy26_apar_score, NULL)), 2) AS avg_apar_score_fy26
      FROM `ongc-hr-finance-agent.hrfin_gold.ssot_workforce_employee`
      GROUP BY wc_id
    ),
    sp AS (
      SELECT
        wc_id,
        SUM(sanctioned_strength) AS sanctioned_strength_fy26,
        SUM(in_position_strength) AS sanctioned_table_in_position_fy26,
        SUM(vacancy_count) AS vacancy_count_fy26,
        ROUND(SAFE_DIVIDE(SUM(vacancy_count) * 100.0, NULLIF(SUM(sanctioned_strength), 0)), 2) AS vacancy_rate_pct_fy26,
        SUM(COALESCE(backlog_vacancies, 0)) AS backlog_vacancies_fy26
      FROM `ongc-hr-finance-agent.hrfin_silver.sanctioned_posts`
      WHERE fiscal_year IN ("FY26", "2026")
      GROUP BY wc_id
    ),
    cw AS (
      SELECT
        wc_id,
        SUM(IF(month = "2026-03", contractor_headcount, 0)) AS contractor_headcount_fy26,
        ROUND(SUM(IF(fiscal_year IN ("FY26", "2026"), monthly_cost_inr, 0)) / 10000000.0, 2) AS contractor_annual_cost_inr_cr_fy26
      FROM `ongc-hr-finance-agent.hrfin_silver.contract_workforce`
      GROUP BY wc_id
    ),
    app AS (
      SELECT
        wc_id,
        COUNT(DISTINCT apprentice_id) AS apprentices_engaged_fy26
      FROM `ongc-hr-finance-agent.hrfin_silver.apprentices`
      WHERE fiscal_year IN ("FY26", "2026")
      GROUP BY wc_id
    ),
    hse AS (
      SELECT
        wc_id,
        COUNT(*) AS hse_incidents_fy26,
        COUNTIF(lost_time_injury_flag = TRUE) AS lti_count_fy26,
        SUM(COALESCE(days_lost, 0)) AS days_lost_fy26,
        ROUND(SAFE_DIVIDE(COUNTIF(lost_time_injury_flag = TRUE) * 1000000.0, NULLIF(SUM(total_manhours_worked), 0)), 3) AS ltifr_fy26
      FROM `ongc-hr-finance-agent.hrfin_silver.hse_incidents`
      WHERE fiscal_year IN ("FY26", "2026")
      GROUP BY wc_id
    ),
    env AS (
      SELECT
        wc_id,
        COUNT(*) AS env_incidents_fy26,
        ROUND(SUM(COALESCE(penalty_inr_lakh, 0)), 2) AS env_penalty_inr_lakh_fy26
      FROM `ongc-hr-finance-agent.hrfin_silver.env_incidents`
      WHERE fiscal_year IN ("FY26", "2026")
      GROUP BY wc_id
    ),
    grv AS (
      SELECT
        wc_id,
        COUNT(*) AS total_grievances_litigation,
        COUNTIF(LOWER(status) IN ("pending", "open", "in_progress", "sub_judice")) AS active_grievances_count
      FROM `ongc-hr-finance-agent.hrfin_silver.grievances_litigation`
      GROUP BY wc_id
    ),
    posh AS (
      SELECT
        wc_id,
        COUNT(*) AS posh_cases_fy26
      FROM `ongc-hr-finance-agent.hrfin_silver.posh_cases`
      WHERE fiscal_year IN ("FY26", "2026")
      GROUP BY wc_id
    ),
    prod AS (
      SELECT
        asset_wc_id AS wc_id,
        oil_production_mmt AS production_oil_mmt_fy26,
        gas_production_bcm AS production_gas_bcm_fy26,
        total_production_boe AS production_total_boe_fy26,
        gross_revenue_inr_cr AS gross_revenue_inr_cr_fy26,
        total_opex_inr_cr AS total_opex_inr_cr_fy26,
        ebitda_inr_cr AS ebitda_inr_cr_fy26,
        manpower_cost_per_boe_usd AS manpower_cost_per_boe_usd_fy26,
        boe_per_employee AS boe_per_employee_fy26
      FROM `ongc-hr-finance-agent.hrfin_gold.mart_asset_productivity`
      WHERE fiscal_year IN ("FY26", "2026")
    ),
    lc AS (
      SELECT
        asset_wc_id AS wc_id,
        lifting_cost_per_boe_usd AS lifting_cost_per_boe_usd_fy26
      FROM `ongc-hr-finance-agent.hrfin_gold.agg_lifting_cost_summary`
      WHERE fiscal_year IN ("FY26", "2026")
    ),
    cpx AS (
      SELECT
        asset_wc_id AS wc_id,
        ROUND(SUM(budget_estimate_be_inr_cr), 2) AS capex_be_inr_cr_fy26,
        ROUND(SUM(revised_estimate_re_inr_cr), 2) AS capex_re_inr_cr_fy26,
        ROUND(SUM(actual_spend_inr_cr), 2) AS capex_actual_inr_cr_fy26,
        ROUND(SAFE_DIVIDE(SUM(actual_spend_inr_cr) * 100.0, NULLIF(SUM(revised_estimate_re_inr_cr), 0)), 2) AS capex_utilisation_pct_fy26
      FROM (
        SELECT DISTINCT budget_id, asset_wc_id, budget_estimate_be_inr_cr, revised_estimate_re_inr_cr, actual_spend_inr_cr
        FROM `ongc-hr-finance-agent.hrfin_silver.capex_budget`
        WHERE fiscal_year IN ("FY26", "2026")
      )
      GROUP BY asset_wc_id
    )
    SELECT
      w.wc_id,
      w.name AS wc_name,
      w.short_name,
      w.city,
      w.state,
      w.sector,
      w.cluster_id,
      w.hard_station_cat,
      w.onshore_offshore,
      w.type AS wc_type,
      w.is_corporate_hq,
      COALESCE(emp.active_headcount, 0) AS active_headcount,
      COALESCE(emp.active_headcount, 0) AS in_position_strength,
      COALESCE(emp.executive_headcount, 0) AS executive_headcount,
      COALESCE(emp.non_executive_headcount, 0) AS non_executive_headcount,
      COALESCE(emp.women_headcount, 0) AS women_headcount,
      COALESCE(emp.women_pct, 0) AS women_pct,
      COALESCE(emp.sc_headcount, 0) AS sc_headcount,
      COALESCE(emp.st_headcount, 0) AS st_headcount,
      COALESCE(emp.obc_headcount, 0) AS obc_headcount,
      COALESCE(emp.pwd_headcount, 0) AS pwd_headcount,
      emp.avg_age_years,
      emp.avg_tenure_years,
      COALESCE(emp.retiring_within_3yr_count, 0) AS retiring_within_3yr_count,
      COALESCE(emp.continuous_stay_5yr_plus_execs, 0) AS continuous_stay_5yr_plus_execs,
      COALESCE(emp.due_for_transfer_execs, 0) AS due_for_transfer_execs,
      COALESCE(sp.sanctioned_strength_fy26, 0) AS sanctioned_strength_fy26,
      COALESCE(sp.vacancy_count_fy26, 0) AS vacancy_count_fy26,
      COALESCE(sp.vacancy_rate_pct_fy26, 0) AS vacancy_rate_pct_fy26,
      COALESCE(sp.backlog_vacancies_fy26, 0) AS backlog_vacancies_fy26,
      COALESCE(cw.contractor_headcount_fy26, 0) AS contractor_headcount_fy26,
      COALESCE(cw.contractor_annual_cost_inr_cr_fy26, 0) AS contractor_annual_cost_inr_cr_fy26,
      ROUND(SAFE_DIVIDE(COALESCE(cw.contractor_headcount_fy26, 0), NULLIF(COALESCE(emp.active_headcount, 0), 0)), 2) AS contractor_to_regular_ratio,
      COALESCE(app.apprentices_engaged_fy26, 0) AS apprentices_engaged_fy26,
      COALESCE(emp.payroll_gross_inr_cr_fy26, 0) AS payroll_gross_inr_cr_fy26,
      COALESCE(emp.overtime_hours_fy26, 0) AS overtime_hours_fy26,
      COALESCE(emp.overtime_cost_inr_cr_fy26, 0) AS overtime_cost_inr_cr_fy26,
      COALESCE(emp.training_hours_fy26, 0) AS training_hours_fy26,
      COALESCE(emp.trained_employees_fy26, 0) AS trained_employees_fy26,
      emp.avg_apar_score_fy26,
      COALESCE(hse.hse_incidents_fy26, 0) AS hse_incidents_fy26,
      COALESCE(hse.lti_count_fy26, 0) AS lti_count_fy26,
      COALESCE(hse.ltifr_fy26, 0) AS ltifr_fy26,
      COALESCE(env.env_incidents_fy26, 0) AS env_incidents_fy26,
      COALESCE(grv.active_grievances_count, 0) AS active_grievances_count,
      COALESCE(posh.posh_cases_fy26, 0) AS posh_cases_fy26,
      COALESCE(prod.production_oil_mmt_fy26, 0) AS production_oil_mmt_fy26,
      COALESCE(prod.production_gas_bcm_fy26, 0) AS production_gas_bcm_fy26,
      COALESCE(prod.production_total_boe_fy26, 0) AS production_total_boe_fy26,
      COALESCE(prod.gross_revenue_inr_cr_fy26, 0) AS gross_revenue_inr_cr_fy26,
      COALESCE(prod.total_opex_inr_cr_fy26, 0) AS total_opex_inr_cr_fy26,
      COALESCE(prod.ebitda_inr_cr_fy26, 0) AS ebitda_inr_cr_fy26,
      lc.lifting_cost_per_boe_usd_fy26,
      prod.manpower_cost_per_boe_usd_fy26,
      prod.boe_per_employee_fy26,
      COALESCE(cpx.capex_be_inr_cr_fy26, 0) AS capex_be_inr_cr_fy26,
      COALESCE(cpx.capex_re_inr_cr_fy26, 0) AS capex_re_inr_cr_fy26,
      COALESCE(cpx.capex_actual_inr_cr_fy26, 0) AS capex_actual_inr_cr_fy26,
      cpx.capex_utilisation_pct_fy26
    FROM `ongc-hr-finance-agent.hrfin_silver.dim_work_centre` w
    LEFT JOIN emp ON w.wc_id = emp.wc_id
    LEFT JOIN sp ON w.wc_id = sp.wc_id
    LEFT JOIN cw ON w.wc_id = cw.wc_id
    LEFT JOIN app ON w.wc_id = app.wc_id
    LEFT JOIN hse ON w.wc_id = hse.wc_id
    LEFT JOIN env ON w.wc_id = env.wc_id
    LEFT JOIN grv ON w.wc_id = grv.wc_id
    LEFT JOIN posh ON w.wc_id = posh.wc_id
    LEFT JOIN prod ON w.wc_id = prod.wc_id
    LEFT JOIN lc ON w.wc_id = lc.wc_id
    LEFT JOIN cpx ON w.wc_id = cpx.wc_id
    """
    client.query(q_ssot_wc).result()
    print("[2/4] Created hrfin_gold.ssot_work_centre_360")

    # 3. Build ssot_field_economics_360 (1 row per field_id x fiscal_year)
    q_ssot_fld = """
    CREATE OR REPLACE TABLE `ongc-hr-finance-agent.hrfin_gold.ssot_field_economics_360`
    CLUSTER BY fiscal_year, onshore_offshore, field_id
    AS
    WITH pm AS (
      SELECT
        field_id,
        fiscal_year,
        SUM(COALESCE(oil_production_mt, 0)) AS oil_production_mt,
        SUM(COALESCE(gas_production_mmscm, 0)) AS gas_production_mmscm,
        SUM(COALESCE(condensate_production_mt, 0)) AS condensate_production_mt,
        ROUND(AVG(water_cut_pct), 2) AS avg_water_cut_pct,
        SUM(COALESCE(well_downtime_hours, 0)) AS total_well_downtime_hours,
        ROUND(AVG(gas_utilisation_pct), 2) AS avg_gas_utilisation_pct,
        MAX(active_producing_wells) AS active_producing_wells
      FROM `ongc-hr-finance-agent.hrfin_silver.production_monthly`
      GROUP BY field_id, fiscal_year
    ),
    res AS (
      SELECT
        field_id,
        fiscal_year,
        MAX(reserves_2p_oil_mmt) AS reserves_2p_oil_mmt,
        MAX(reserves_2p_gas_bcm) AS reserves_2p_gas_bcm,
        MAX(reserves_2p_total_mmtoe) AS reserves_2p_total_mmtoe,
        MAX(reserve_replacement_ratio_rrr_2p) AS reserve_replacement_ratio_rrr_2p,
        MAX(finding_cost_usd_per_boe) AS finding_cost_usd_per_boe,
        MAX(development_cost_usd_per_boe) AS development_cost_usd_per_boe
      FROM `ongc-hr-finance-agent.hrfin_silver.reserves_annual`
      GROUP BY field_id, fiscal_year
    ),
    wl AS (
      SELECT
        field_id,
        fiscal_year,
        COUNT(*) AS wells_drilled_count,
        COUNTIF(LOWER(well_type) LIKE "%explor%") AS exploratory_wells_count,
        COUNTIF(LOWER(well_type) LIKE "%dev%") AS development_wells_count,
        COUNTIF(LOWER(result_status) = "dry_hole") AS dry_holes_count,
        ROUND(SUM(COALESCE(drilling_cost_inr_cr, 0)), 2) AS drilling_cost_inr_cr
      FROM `ongc-hr-finance-agent.hrfin_silver.wells_drilled`
      GROUP BY field_id, fiscal_year
    )
    SELECT
      p.pnl_id,
      p.fiscal_year,
      p.field_id,
      p.field_name,
      p.basin,
      p.onshore_offshore,
      f.maturity,
      p.asset_wc_id,
      p.asset_name,
      COALESCE(pm.oil_production_mt, 0) AS oil_production_mt,
      COALESCE(pm.gas_production_mmscm, 0) AS gas_production_mmscm,
      COALESCE(pm.condensate_production_mt, 0) AS condensate_production_mt,
      p.total_production_boe,
      pm.avg_water_cut_pct AS water_cut_pct,
      COALESCE(pm.total_well_downtime_hours, 0) AS well_downtime_hours,
      pm.avg_gas_utilisation_pct AS gas_utilisation_pct,
      COALESCE(pm.active_producing_wells, 0) AS active_producing_wells,
      p.oil_revenue_inr_cr,
      p.gas_revenue_inr_cr,
      p.recomputed_gross_revenue_inr_cr AS gross_revenue_inr_cr,
      p.recomputed_gross_revenue_inr_cr,
      p.statutory_royalty_inr_cr,
      p.statutory_cess_inr_cr,
      p.statutory_windfall_tax_saed_inr_cr,
      p.recomputed_net_revenue_inr_cr AS net_revenue_inr_cr,
      p.recomputed_net_revenue_inr_cr,
      p.allocated_manpower_cost_inr_cr,
      p.total_opex_inr_cr,
      p.recomputed_ebitda_inr_cr AS ebitda_inr_cr,
      p.recomputed_ebitda_inr_cr,
      p.recomputed_ebitda_margin_pct AS ebitda_margin_pct,
      p.dda_depreciation_inr_cr,
      p.recomputed_pbt_inr_cr AS pbt_inr_cr,
      p.recomputed_pbt_inr_cr,
      p.lifting_cost_per_boe_usd,
      p.manpower_cost_per_boe_usd,
      p.boe_per_employee,
      p.is_loss_making_3yr_consecutive,
      p.is_divestment_candidate,
      p.pec_monetisation_potential_flag,
      p.root_cause_loss_code,
      res.reserves_2p_oil_mmt,
      res.reserves_2p_gas_bcm,
      res.reserves_2p_total_mmtoe,
      res.reserve_replacement_ratio_rrr_2p,
      res.finding_cost_usd_per_boe,
      res.development_cost_usd_per_boe,
      COALESCE(wl.wells_drilled_count, 0) AS wells_drilled_count,
      COALESCE(wl.exploratory_wells_count, 0) AS exploratory_wells_count,
      COALESCE(wl.development_wells_count, 0) AS development_wells_count,
      COALESCE(wl.dry_holes_count, 0) AS dry_holes_count,
      COALESCE(wl.drilling_cost_inr_cr, 0) AS drilling_cost_inr_cr
    FROM `ongc-hr-finance-agent.hrfin_gold.agg_field_pnl_summary` p
    LEFT JOIN `ongc-hr-finance-agent.hrfin_silver.dim_field` f ON p.field_id = f.field_id
    LEFT JOIN pm ON p.field_id = pm.field_id AND p.fiscal_year = pm.fiscal_year
    LEFT JOIN res ON p.field_id = res.field_id AND p.fiscal_year = res.fiscal_year
    LEFT JOIN wl ON p.field_id = wl.field_id AND p.fiscal_year = wl.fiscal_year
    WHERE p.field_id IS NOT NULL
    """
    client.query(q_ssot_fld).result()
    print("[3/4] Created hrfin_gold.ssot_field_economics_360")

    # 4. Build ssot_corporate_annual_360 (1 row per fiscal_year)
    q_ssot_corp = """
    CREATE OR REPLACE TABLE `ongc-hr-finance-agent.hrfin_gold.ssot_corporate_annual_360`
    AS
    WITH csr AS (
      SELECT fiscal_year, ROUND(SUM(actual_disbursed_inr_cr), 2) AS csr_disbursed_inr_cr, SUM(beneficiaries_count) AS csr_beneficiaries
      FROM `ongc-hr-finance-agent.hrfin_silver.csr_projects`
      GROUP BY fiscal_year
    ),
    mou AS (
      SELECT fiscal_year, ROUND(MAX(composite_score), 2) AS mou_composite_score, MAX(achieved_rating) AS mou_rating
      FROM `ongc-hr-finance-agent.hrfin_silver.mou_targets`
      GROUP BY fiscal_year
    ),
    ar AS (
      SELECT fiscal_year, ROUND(SUM(outstanding_amount_inr_cr), 2) AS receivables_outstanding_inr_cr, ROUND(SUM(IF(is_disputed, outstanding_amount_inr_cr, 0)), 2) AS disputed_receivables_inr_cr
      FROM `ongc-hr-finance-agent.hrfin_silver.receivables`
      GROUP BY fiscal_year
    ),
    bl AS (
      SELECT fiscal_year, ROUND(SUM(actuarial_liability_inr_cr), 2) AS actuarial_liability_inr_cr, ROUND(SUM(net_liability_inr_cr), 2) AS net_benefit_liability_inr_cr
      FROM `ongc-hr-finance-agent.hrfin_silver.benefit_liabilities`
      GROUP BY fiscal_year
    ),
    et AS (
      SELECT fiscal_year, ROUND(SUM(installed_capacity_mw), 2) AS renewable_installed_mw, ROUND(SUM(generation_gwh), 2) AS renewable_generation_gwh, ROUND(SUM(annual_capex_inr_cr), 2) AS green_capex_inr_cr
      FROM `ongc-hr-finance-agent.hrfin_silver.energy_transition`
      GROUP BY fiscal_year
    ),
    app AS (
      SELECT fiscal_year, COUNT(DISTINCT apprentice_id) AS apprentices_engaged
      FROM `ongc-hr-finance-agent.hrfin_silver.apprentices`
      GROUP BY fiscal_year
    )
    SELECT
      cf.fiscal_year,
      cf.gross_revenue_inr_cr,
      cf.offshore_revenue_inr_cr,
      cf.onshore_revenue_inr_cr,
      cf.statutory_levies_total_inr_cr,
      cf.royalty_inr_cr,
      cf.oidb_cess_inr_cr,
      cf.saed_windfall_tax_inr_cr,
      cf.employee_cost_total_inr_cr,
      cf.operating_expenses_total_inr_cr,
      cf.ebitda_inr_cr,
      cf.dda_inr_cr,
      cf.pbt_inr_cr,
      cf.pat_inr_cr,
      cf.total_capex_spent_inr_cr,
      cf.dividend_per_share_inr,
      cf.total_dividend_payout_inr_cr,
      cf.dividend_payout_ratio_pct,
      cf.lifting_cost_average_usd_boe,
      cf.standalone_roce_pct,
      cf.consolidated_pat_inr_cr,
      cf.consolidated_roce_pct,
      COALESCE(csr.csr_disbursed_inr_cr, 0) AS csr_disbursed_inr_cr,
      COALESCE(csr.csr_beneficiaries, 0) AS csr_beneficiaries,
      mou.mou_composite_score,
      mou.mou_rating,
      COALESCE(ar.receivables_outstanding_inr_cr, 0) AS receivables_outstanding_inr_cr,
      COALESCE(ar.disputed_receivables_inr_cr, 0) AS disputed_receivables_inr_cr,
      COALESCE(bl.actuarial_liability_inr_cr, 0) AS actuarial_liability_inr_cr,
      COALESCE(bl.net_benefit_liability_inr_cr, 0) AS net_benefit_liability_inr_cr,
      COALESCE(et.renewable_installed_mw, 0) AS renewable_installed_mw,
      COALESCE(et.renewable_generation_gwh, 0) AS renewable_generation_gwh,
      COALESCE(et.green_capex_inr_cr, 0) AS green_capex_inr_cr,
      COALESCE(app.apprentices_engaged, 0) AS apprentices_engaged
    FROM `ongc-hr-finance-agent.hrfin_silver.corporate_financials` cf
    LEFT JOIN csr ON cf.fiscal_year = csr.fiscal_year
    LEFT JOIN mou ON cf.fiscal_year = mou.fiscal_year
    LEFT JOIN ar ON cf.fiscal_year = ar.fiscal_year
    LEFT JOIN bl ON cf.fiscal_year = bl.fiscal_year
    LEFT JOIN et ON cf.fiscal_year = et.fiscal_year
    LEFT JOIN app ON cf.fiscal_year = app.fiscal_year
    ORDER BY cf.fiscal_year
    """
    client.query(q_ssot_corp).result()
    print("[4/4] Created hrfin_gold.ssot_corporate_annual_360")

    # Verify SSOT tables
    for tbl in [
        "ssot_workforce_employee",
        "ssot_work_centre_360",
        "ssot_field_economics_360",
        "ssot_corporate_annual_360",
    ]:
        t = client.get_table(f"{GCP_PROJECT}.hrfin_gold.{tbl}")
        print(f"Verified hrfin_gold.{tbl}: {t.num_rows} rows, {len(t.schema)} columns")

    # Verify Ahmedabad 360 row
    ahm = list(
        client.query(
            "SELECT wc_id, wc_name, active_headcount, executive_headcount, non_executive_headcount, sanctioned_strength_fy26, vacancy_count_fy26, contractor_headcount_fy26, payroll_gross_inr_cr_fy26 FROM `ongc-hr-finance-agent.hrfin_gold.ssot_work_centre_360` WHERE wc_id = 'WC-AHM'"
        ).result()
    )[0]
    print("Ahmedabad SSOT 360:", dict(ahm))


if __name__ == "__main__":
    main()
