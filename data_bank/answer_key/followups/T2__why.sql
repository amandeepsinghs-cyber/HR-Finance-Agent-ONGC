-- Answer Key Follow-up SQL: T2__why
-- Question: Why have these specific officers remained at corporate headquarters beyond the 10-year cumulative cap?
-- Type: chain
-- Semantic audit 2026-10-20: Old SQL used single-posting tenure >= 60 months (not the 10-year cumulative cap) and grouped by exemption tag, intending to impute reasons via COALESCE(...,'Impending_Retirement'/'CMD') (silver stores the string 'None').
-- Semantic audit 2026-10-20: Now: everyone currently in cluster CL-DEL by cadre - cumulative years, 10-year cap breaches (JRTP 4.1), superannuation exemption and recorded exemptions. Shows no executive has breached the cap.

WITH cl AS (
    SELECT emp_id, current_grade_id, cumulative_cluster_years, has_breached_cluster_10yr_cap, is_superannuation_exempt
    FROM `ongc-hr-finance-agent.hrfin_gold.v_cluster_cumulative_tenure`
    WHERE cluster_id = 'CL-DEL' AND is_currently_in_cluster
),
ph AS (
    SELECT emp_id, NULLIF(exemption_tag, 'None') AS exemption_tag
    FROM posting_history
    WHERE is_current_posting AND wc_id = 'WC-DEL'
)
SELECT
    g.cadre,
    COUNT(DISTINCT cl.emp_id) AS currently_in_delhi,
    COUNT(DISTINCT IF(cl.cumulative_cluster_years >= 5, cl.emp_id, NULL)) AS cumulative_5yr_plus,
    COUNT(DISTINCT IF(cl.has_breached_cluster_10yr_cap, cl.emp_id, NULL)) AS breached_10yr_cap,
    COUNT(DISTINCT IF(cl.has_breached_cluster_10yr_cap AND cl.is_superannuation_exempt, cl.emp_id, NULL)) AS breached_and_superannuation_exempt,
    COUNT(DISTINCT IF(ph.exemption_tag IS NOT NULL, cl.emp_id, NULL)) AS with_recorded_exemption,
    ROUND(MAX(cl.cumulative_cluster_years), 1) AS max_cumulative_years
FROM cl
JOIN dim_grade g ON g.grade_id = cl.current_grade_id
LEFT JOIN ph ON ph.emp_id = cl.emp_id
GROUP BY g.cadre
ORDER BY breached_10yr_cap DESC, currently_in_delhi DESC;
