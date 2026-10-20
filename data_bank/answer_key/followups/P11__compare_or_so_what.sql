-- Answer Key Follow-up SQL: P11__compare_or_so_what
-- Question: What would be the net change in Delhi office staffing if all non-exempt tenure-breaching officers are rotated?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL counted all staff (incl. Group C/D) in every cluster. Now executives only (JRTP scope),
-- Semantic audit 2026-10-20: per cluster, with net change = -(non-exempt breaching executives); Delhi row is the answer,
-- Semantic audit 2026-10-20: other clusters show where the rotation load actually sits.
SELECT
    v.cluster_name,
    v.cluster_id = 'CL-DEL' AS is_delhi,
    COUNT(DISTINCT v.emp_id) AS executives_in_cluster,
    COUNT(DISTINCT IF(v.has_breached_cluster_10yr_cap, v.emp_id, NULL)) AS breached_10yr_cap,
    COUNT(DISTINCT IF(v.has_breached_cluster_10yr_cap AND DATE_DIFF(v.retirement_date, DATE '2026-10-19', DAY) <= 3 * 365.25, v.emp_id, NULL)) AS exempt_retiring_3yr,
    COUNT(DISTINCT IF(v.has_breached_cluster_10yr_cap AND DATE_DIFF(v.retirement_date, DATE '2026-10-19', DAY) > 3 * 365.25, v.emp_id, NULL)) AS non_exempt_to_rotate,
    COUNT(DISTINCT v.emp_id) - COUNT(DISTINCT IF(v.has_breached_cluster_10yr_cap AND DATE_DIFF(v.retirement_date, DATE '2026-10-19', DAY) > 3 * 365.25, v.emp_id, NULL)) AS executives_after_rotation,
    ROUND(-100 * COUNT(DISTINCT IF(v.has_breached_cluster_10yr_cap AND DATE_DIFF(v.retirement_date, DATE '2026-10-19', DAY) > 3 * 365.25, v.emp_id, NULL)) / COUNT(DISTINCT v.emp_id), 1) AS net_change_pct
FROM `ongc-hr-finance-agent.hrfin_gold.v_cluster_cumulative_tenure` v
JOIN dim_grade g ON g.grade_id = v.current_grade_id
WHERE v.is_currently_in_cluster AND LOWER(g.cadre) = 'executive'
GROUP BY v.cluster_name, v.cluster_id
ORDER BY is_delhi DESC, non_exempt_to_rotate DESC;
