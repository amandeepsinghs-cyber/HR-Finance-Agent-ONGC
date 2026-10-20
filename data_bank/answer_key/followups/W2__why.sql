-- Answer Key Follow-up SQL: W2__why
-- Question: Why does the projected retirement cliff disproportionately deplete executive technical talent in senior grades?
-- Type: what_if
-- Semantic audit 2026-10-20: Old SQL counted retirements by grade group across all disciplines and had no denominator, so 'disproportionate' could not be shown.
-- Semantic audit 2026-10-20: Now: technical-function executives by grade - headcount, retirements to Oct-2028, retirement share and average age.

SELECT
    g.grade_id,
    g.designation,
    COUNT(DISTINCT e.emp_id) AS technical_executives,
    COUNT(DISTINCT IF(e.retirement_date BETWEEN DATE '2026-10-20' AND DATE '2028-10-19', e.emp_id, NULL)) AS retiring_by_oct2028,
    ROUND(COUNT(DISTINCT IF(e.retirement_date BETWEEN DATE '2026-10-20' AND DATE '2028-10-19', e.emp_id, NULL)) * 100.0 / NULLIF(COUNT(DISTINCT e.emp_id), 0), 1) AS retiring_pct,
    ROUND(AVG(e.age_years), 1) AS avg_age
FROM employee_master e
JOIN dim_grade g ON g.grade_id = e.current_grade_id
JOIN dim_discipline d ON d.discipline_id = e.discipline_id
WHERE LOWER(e.employment_status) = 'active'
  AND LOWER(g.cadre) = 'executive'
  AND LOWER(d.function) = 'technical'
GROUP BY g.grade_id, g.designation, g.level_order
ORDER BY g.level_order;
