-- Answer Key SQL: W2
-- Question: If we freeze hiring for 2 years, what will headcount be by discipline in 2028, given retirements?
-- Type: what_if
-- Semantic audit 2026-10-20: Old SQL restricted 'headcount' to executives only (13,453 of 22,798), silently dropping 9,345 non-executives from discipline headcounts.
-- Semantic audit 2026-10-20: Now: whole active workforce by discipline (executives shown separately), retirements 20-Oct-2026..19-Oct-2028, projected headcount under a 2-year hiring freeze (retirement-only attrition).

SELECT
    d.discipline_id,
    d.name AS discipline_name,
    COUNT(DISTINCT e.emp_id) AS current_headcount,
    COUNT(DISTINCT IF(e.current_grade_id LIKE 'E%', e.emp_id, NULL)) AS current_executives,
    COUNT(DISTINCT IF(e.retirement_date BETWEEN DATE '2026-10-20' AND DATE '2028-10-19', e.emp_id, NULL)) AS retirements_by_oct2028,
    COUNT(DISTINCT e.emp_id) - COUNT(DISTINCT IF(e.retirement_date BETWEEN DATE '2026-10-20' AND DATE '2028-10-19', e.emp_id, NULL)) AS projected_headcount_oct2028,
    ROUND(-COUNT(DISTINCT IF(e.retirement_date BETWEEN DATE '2026-10-20' AND DATE '2028-10-19', e.emp_id, NULL)) * 100.0 / NULLIF(COUNT(DISTINCT e.emp_id), 0), 1) AS change_pct
FROM employee_master e
JOIN dim_discipline d ON e.discipline_id = d.discipline_id
WHERE LOWER(e.employment_status) = 'active'
GROUP BY d.discipline_id, d.name
ORDER BY current_headcount DESC;
