-- Answer Key Follow-up SQL: P11__drill_down
-- Question: List the 138 executives in Delhi who have exceeded the 10-year cumulative cap, filtered by discipline and grade.
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL listed Group C/D + CMD (outside JRTP scope) as "executives". Restricted to executives
-- Semantic audit 2026-10-20: (dim_grade.cadre='executive'); the premise of 138 breaching executives is not supported by
-- Semantic audit 2026-10-20: posting_history (0 breach), so the drill-down shows executives by grade with distance to the cap.
SELECT
    v.current_grade_id AS grade_id,
    COUNT(DISTINCT v.emp_id) AS executives_in_delhi,
    COUNT(DISTINCT IF(v.has_breached_cluster_10yr_cap, v.emp_id, NULL)) AS breached_10yr_cap,
    COUNT(DISTINCT IF(v.cumulative_cluster_years >= 8, v.emp_id, NULL)) AS approaching_cap_8yr_plus,
    COUNT(DISTINCT IF(v.cumulative_cluster_years >= 5, v.emp_id, NULL)) AS over_5yr_in_cluster,
    ROUND(MAX(v.cumulative_cluster_years), 2) AS max_cumulative_years,
    COUNT(DISTINCT IF(DATE_DIFF(v.retirement_date, DATE '2026-10-19', DAY) <= 3 * 365.25, v.emp_id, NULL)) AS retiring_within_3yr
FROM `ongc-hr-finance-agent.hrfin_gold.v_cluster_cumulative_tenure` v
JOIN dim_grade g ON g.grade_id = v.current_grade_id
WHERE v.cluster_id = 'CL-DEL' AND v.is_currently_in_cluster AND LOWER(g.cadre) = 'executive'
GROUP BY v.current_grade_id
ORDER BY v.current_grade_id;
