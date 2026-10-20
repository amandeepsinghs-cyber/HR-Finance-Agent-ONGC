-- Answer Key Follow-up SQL: C1__compare_or_so_what
-- Question: How does the Delhi retention rate compare with corporate headquarters in Dehradun (Tel Bhavan) and Mumbai?
-- Type: data
-- Semantic audit 2026-10-20: filter w.city IN ('Delhi','Dehradun','Mumbai') silently dropped Delhi (city is
-- 'New Delhi') and pooled every Dehradun institute and every Mumbai offshore asset into "HQ". Now the three
-- corporate offices are selected by wc_id (WC-DEL Delhi HQ, WC-DDN Tel Bhavan, WC-ROM Regional Office Mumbai)
-- plus a company-wide executive benchmark row. Retention rate = % of current executives with >= 60 months
-- continuous stay at that work centre.

WITH base AS (
    SELECT v.wc_id, v.emp_id, v.continuous_stay_months
    FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay` v
    WHERE v.is_current_stay = TRUE
      AND v.grade_id LIKE 'E%'
)
SELECT
    w.wc_id,
    w.short_name,
    w.city,
    COUNT(DISTINCT CASE WHEN b.continuous_stay_months >= 60 THEN b.emp_id END) AS executives_ge_5yr,
    COUNT(DISTINCT b.emp_id) AS total_current_executives,
    ROUND(COUNT(DISTINCT CASE WHEN b.continuous_stay_months >= 60 THEN b.emp_id END) * 100.0 / NULLIF(COUNT(DISTINCT b.emp_id), 0), 1) AS pct_stay_ge_5yr,
    ROUND(AVG(b.continuous_stay_months) / 12.0, 1) AS avg_continuous_stay_years
FROM base b
JOIN dim_work_centre w ON b.wc_id = w.wc_id
WHERE w.wc_id IN ('WC-DEL', 'WC-DDN', 'WC-ROM')
GROUP BY w.wc_id, w.short_name, w.city
UNION ALL
SELECT
    'ALL',
    'Company (all work centres)',
    'All',
    COUNT(DISTINCT CASE WHEN continuous_stay_months >= 60 THEN emp_id END),
    COUNT(DISTINCT emp_id),
    ROUND(COUNT(DISTINCT CASE WHEN continuous_stay_months >= 60 THEN emp_id END) * 100.0 / NULLIF(COUNT(DISTINCT emp_id), 0), 1),
    ROUND(AVG(continuous_stay_months) / 12.0, 1)
FROM base
ORDER BY pct_stay_ge_5yr DESC;
