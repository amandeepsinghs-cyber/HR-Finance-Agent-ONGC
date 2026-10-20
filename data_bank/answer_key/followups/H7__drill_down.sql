-- Answer Key Follow-up SQL: H7__drill_down
-- Question: How many women executives are currently deployed in rotational offshore shifts on Mumbai High platforms and rigs?
-- Type: data
-- Semantic audit 2026-10-20: old SQL counted women of ALL grades and admitted separated staff via 'OR separation_date IS NULL'.
-- Now: active women EXECUTIVES (cadre='executive') currently posted to offshore work centres, with total executives and share.
SELECT
    wc.short_name AS work_centre,
    COUNTIF(LOWER(e.gender) = 'female') AS women_executives,
    COUNT(*) AS executives,
    ROUND(COUNTIF(LOWER(e.gender) = 'female') * 100.0 / COUNT(*), 1) AS women_pct
FROM employee_master e
JOIN dim_work_centre wc ON e.current_wc_id = wc.wc_id
JOIN dim_grade g ON g.grade_id = e.current_grade_id
WHERE LOWER(e.employment_status) = 'active'
  AND LOWER(g.cadre) = 'executive'
  AND LOWER(wc.onshore_offshore) = 'offshore'
GROUP BY wc.short_name
ORDER BY women_executives DESC, work_centre;
