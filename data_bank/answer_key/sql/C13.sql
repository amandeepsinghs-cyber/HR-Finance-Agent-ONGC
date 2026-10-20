-- Answer Key SQL: C13
-- Question: If we move 200 executives from Delhi/Dehradun to field assets, what changes in cost and coverage?
-- Type: what_if
-- Semantic audit 2026-10-20: old SQL hard-coded the cost (6.50 AS estimated_cta_outlay_cr, i.e. an assumed
-- Rs 3.25 lakh per officer), summed sanctioned/in-position strength over ALL grades for four hand-picked
-- assets, and never allocated the 200 officers. Now a parameterised scenario:
--   * movers: 200 E3-E5 executives (scenario parameter from the question) from WC-DEL + WC-DDN; the source
--     pool size and how many of them are already overdue for rotation (>= 60 months, outside the 3-year
--     pre-retirement protection) are shown;
--   * one-time cost: average actual total transfer cost (transfer grant + CTA + baggage) of E3-E5
--     rotation / hard-station postings in FY24-FY26 from posting_history, x officers allocated;
--   * recurring cost: Special Hard Station Allowance = 10% of basic pay (JRTP Clause 6.3) for officers
--     placed in Category-C assets, using the FY26 average annual basic pay of the Delhi/Dehradun E3-E5 pool;
--   * coverage: the 200 are allocated to field assets (dim_work_centre.type = 'asset') pro-rata to their FY26
--     executive vacancy (sanctioned_posts, E-grades), capped at each asset's vacancy.
-- Salaries move with the officers, so there is no payroll saving; HQ strength falls by the number moved.
-- Semantic audit 2026-10-20 (alignment with C1/H10/X10): overdue pool also excludes executives whose current
-- posting carries a valid exemption_tag ('None' = no tag; exemption_valid_until >= 2026-10-19 or NULL).

WITH params AS (SELECT 200 AS officers),
pool AS (
    SELECT
        COUNT(DISTINCT e.emp_id) AS source_pool_e3_e5,
        COUNT(DISTINCT IF(v.continuous_stay_months >= 60 AND DATE_DIFF(v.retirement_date, DATE '2026-10-19', DAY) > 3 * 365.25 AND ex.emp_id IS NULL, e.emp_id, NULL)) AS source_pool_overdue
    FROM employee_master e
    LEFT JOIN `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay` v ON v.emp_id = e.emp_id AND v.is_current_stay
    LEFT JOIN (SELECT DISTINCT emp_id FROM posting_history WHERE is_current_posting = TRUE AND NULLIF(exemption_tag, 'None') IS NOT NULL
               AND (exemption_valid_until >= DATE '2026-10-19' OR exemption_valid_until IS NULL)) ex ON ex.emp_id = e.emp_id
    WHERE LOWER(e.employment_status) = 'active' AND e.current_wc_id IN ('WC-DEL', 'WC-DDN') AND e.current_grade_id IN ('E3', 'E4', 'E5')
),
basic AS (
    SELECT SUM(p.basic_pay_inr) / COUNT(DISTINCT p.emp_id) AS avg_annual_basic_inr
    FROM payroll_monthly p
    JOIN employee_master e ON e.emp_id = p.emp_id
    WHERE p.fiscal_year = 'FY26' AND p.grade_id IN ('E3', 'E4', 'E5') AND p.wc_id IN ('WC-DEL', 'WC-DDN')
),
tcost AS (
    SELECT AVG(total_transfer_cost_inr) AS avg_transfer_cost_inr
    FROM posting_history
    WHERE fiscal_year IN ('FY24', 'FY25', 'FY26') AND grade_id IN ('E3', 'E4', 'E5')
      AND LOWER(posting_type) IN ('rotation', 'hard_station') AND total_transfer_cost_inr > 0
),
vac AS (
    SELECT w.wc_id, w.short_name, w.hard_station_cat,
           SUM(sp.sanctioned_strength) AS exec_sanctioned, SUM(sp.in_position_strength) AS exec_in_position, SUM(sp.vacancy_count) AS exec_vacancy
    FROM sanctioned_posts sp
    JOIN dim_work_centre w ON w.wc_id = sp.wc_id
    WHERE sp.fiscal_year = 'FY26' AND sp.grade_id LIKE 'E%' AND LOWER(w.type) = 'asset'
    GROUP BY 1, 2, 3
    HAVING SUM(sp.vacancy_count) > 0
),
alloc AS (
    SELECT v.*, LEAST(v.exec_vacancy, CAST(ROUND(p.officers * v.exec_vacancy / SUM(v.exec_vacancy) OVER ()) AS INT64)) AS allocated_officers
    FROM vac v CROSS JOIN params p
),
rows_ AS (
    SELECT 'receiving_asset' AS section, 0 AS ord, a.short_name AS entity, a.hard_station_cat,
           a.exec_sanctioned, a.exec_in_position, a.exec_vacancy, a.allocated_officers,
           a.allocated_officers * t.avg_transfer_cost_inr / 1e7 AS one_time_cost_cr,
           IF(a.hard_station_cat = 'C', a.allocated_officers * b.avg_annual_basic_inr * 0.10 / 1e7, 0) AS annual_allowance_cr
    FROM alloc a CROSS JOIN tcost t CROSS JOIN basic b
)
SELECT
    r.section, r.entity, r.hard_station_cat, r.exec_sanctioned, r.exec_in_position, r.exec_vacancy, r.allocated_officers,
    r.exec_vacancy - r.allocated_officers AS vacancy_after_move,
    ROUND(r.exec_in_position * 100.0 / NULLIF(r.exec_sanctioned, 0), 1) AS fill_pct_before,
    ROUND((r.exec_in_position + r.allocated_officers) * 100.0 / NULLIF(r.exec_sanctioned, 0), 1) AS fill_pct_after,
    ROUND(r.one_time_cost_cr, 2) AS one_time_transfer_cost_cr,
    ROUND(r.annual_allowance_cr, 2) AS annual_hard_station_allowance_cr,
    CAST(NULL AS INT64) AS source_pool_e3_e5, CAST(NULL AS INT64) AS source_pool_overdue,
    CAST(NULL AS FLOAT64) AS avg_transfer_cost_lakh
FROM rows_ r
UNION ALL
SELECT
    'scenario_total', 'All receiving field assets', NULL,
    SUM(r.exec_sanctioned), SUM(r.exec_in_position), SUM(r.exec_vacancy), SUM(r.allocated_officers),
    SUM(r.exec_vacancy) - SUM(r.allocated_officers),
    ROUND(SUM(r.exec_in_position) * 100.0 / NULLIF(SUM(r.exec_sanctioned), 0), 1),
    ROUND((SUM(r.exec_in_position) + SUM(r.allocated_officers)) * 100.0 / NULLIF(SUM(r.exec_sanctioned), 0), 1),
    ROUND(SUM(r.one_time_cost_cr), 2), ROUND(SUM(r.annual_allowance_cr), 2),
    ANY_VALUE(pool.source_pool_e3_e5), ANY_VALUE(pool.source_pool_overdue),
    ROUND(ANY_VALUE(t.avg_transfer_cost_inr) / 1e5, 2)
FROM rows_ r CROSS JOIN pool CROSS JOIN tcost t
ORDER BY section, allocated_officers DESC;
