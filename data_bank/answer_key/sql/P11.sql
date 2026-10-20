-- Answer Key SQL: P11
-- Question: Under the transfer policy, who in Delhi has exceeded the cumulative-tenure cap, and who is exempt because they retire soon?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: JRTP Clause 1.2 applies only to regular executives E0-E9. Old SQL counted every staff member
-- Semantic audit 2026-10-20: currently in CL-DEL (200 Group C/D non-executives + the CMD) and labelled them "executives".
-- Semantic audit 2026-10-20: Now split by staff population via dim_grade.cadre; only the 'executive' row is in JRTP scope.
-- Semantic audit 2026-10-20: Exemption = retirement within 3 years of 2026-10-19 (Clause 7.1 practice; 2-year strict rule also shown).
WITH delhi AS (
    SELECT v.emp_id, v.cumulative_cluster_years, v.has_breached_cluster_10yr_cap, v.retirement_date, g.cadre
    FROM `ongc-hr-finance-agent.hrfin_gold.v_cluster_cumulative_tenure` v
    JOIN dim_grade g ON g.grade_id = v.current_grade_id
    WHERE v.cluster_id = 'CL-DEL' AND v.is_currently_in_cluster
)
SELECT
    CASE LOWER(cadre) WHEN 'executive' THEN 'Executives E0-E9 (JRTP scope)'
                      WHEN 'non_executive' THEN 'Non-executives Group B/C/D (outside JRTP)'
                      ELSE 'Board - CMD/Directors (outside JRTP)' END AS staff_population,
    LOWER(cadre) = 'executive' AS in_jrtp_scope,
    COUNT(DISTINCT emp_id) AS currently_in_delhi_cluster,
    ROUND(MAX(cumulative_cluster_years), 2) AS max_cumulative_years,
    COUNT(DISTINCT IF(cumulative_cluster_years >= 8, emp_id, NULL)) AS approaching_cap_8yr_plus,
    COUNT(DISTINCT IF(has_breached_cluster_10yr_cap, emp_id, NULL)) AS breached_10yr_cap,
    COUNT(DISTINCT IF(has_breached_cluster_10yr_cap AND DATE_DIFF(retirement_date, DATE '2026-10-19', DAY) <= 3 * 365.25, emp_id, NULL)) AS breached_exempt_retiring_3yr,
    COUNT(DISTINCT IF(has_breached_cluster_10yr_cap AND DATE_DIFF(retirement_date, DATE '2026-10-19', DAY) > 3 * 365.25, emp_id, NULL)) AS breached_due_transfer,
    COUNT(DISTINCT IF(DATE_DIFF(retirement_date, DATE '2026-10-19', DAY) <= 2 * 365.25, emp_id, NULL)) AS retiring_within_2yr,
    COUNT(DISTINCT IF(DATE_DIFF(retirement_date, DATE '2026-10-19', DAY) <= 3 * 365.25, emp_id, NULL)) AS retiring_within_3yr
FROM delhi
GROUP BY 1, 2
ORDER BY in_jrtp_scope DESC, staff_population;
