-- Answer Key SQL: C5
-- Question: Which disciplines (geoscience, drilling, reservoir, production) face the biggest retirement-driven skill gap by 2030?
-- Type: data
-- Semantic audit 2026-10-20: counts were correct (retiring by 31-Mar-2030 = end of FY30) but the status filter
-- "employment_status = 'Active' OR separation_date IS NULL" is replaced by LOWER(employment_status) = 'active'
-- and the retirement test now uses retirement_date (same result, explicit). Added Geophysics (Wells) to the
-- geoscience set and an E0-E2 junior pipeline column so the "gap" can be read against replacement depth.

SELECT
    d.discipline_id,
    d.name AS discipline_name,
    COUNT(DISTINCT e.emp_id) AS active_executives,
    COUNT(DISTINCT CASE WHEN e.retirement_date <= DATE '2030-03-31' THEN e.emp_id END) AS retiring_by_fy30,
    ROUND(COUNT(DISTINCT CASE WHEN e.retirement_date <= DATE '2030-03-31' THEN e.emp_id END) * 100.0 / NULLIF(COUNT(DISTINCT e.emp_id), 0), 1) AS retirement_pct,
    COUNT(DISTINCT CASE WHEN e.retirement_date <= DATE '2030-03-31' AND e.current_grade_id IN ('E5', 'E6', 'E7', 'E8', 'E9') THEN e.emp_id END) AS retiring_by_fy30_e5_plus,
    COUNT(DISTINCT CASE WHEN e.current_grade_id IN ('E0', 'E1', 'E2') THEN e.emp_id END) AS e0_e2_pipeline
FROM employee_master e
JOIN dim_discipline d ON e.discipline_id = d.discipline_id
WHERE e.current_grade_id LIKE 'E%'
  AND d.discipline_id IN ('DISC-DRL', 'DISC-GEO', 'DISC-GPS', 'DISC-GPW', 'DISC-RES', 'DISC-PRD')
  AND LOWER(e.employment_status) = 'active'
GROUP BY d.discipline_id, d.name
ORDER BY retiring_by_fy30 DESC;
