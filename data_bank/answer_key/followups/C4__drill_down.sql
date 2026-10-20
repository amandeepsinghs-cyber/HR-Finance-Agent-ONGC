-- Answer Key Follow-up SQL: C4__drill_down
-- Question: Which key operational roles in Offshore (Mumbai High, Neelam-Heera) and Drilling have retirement vacancies within 12 months?
-- Type: data
-- Semantic audit 2026-10-20: old SQL listed succession-plan positions retiring in 12 months at ANY work centre
-- (Delhi CMD, Bassein GMs...), included incumbents who have already separated, and ignored the offshore /
-- drilling scope. Now: active executives at Mumbai High (WC-MUM), Neelam & Heera (WC-NEH) and Corporate
-- Drilling Services (WC-DRL) whose retirement_date falls in the next 12 months (2026-10-19 .. 2027-10-18),
-- by work centre and discipline, split senior (E5+) vs other, with the number holding a succession-plan role.

SELECT
    w.short_name AS work_centre,
    d.name AS discipline_name,
    COUNT(DISTINCT e.emp_id) AS retiring_12m,
    COUNT(DISTINCT IF(e.current_grade_id IN ('E5', 'E6', 'E7', 'E8', 'E9'), e.emp_id, NULL)) AS retiring_12m_e5_plus,
    COUNT(DISTINCT IF(e.current_grade_id IN ('E7', 'E8', 'E9'), e.emp_id, NULL)) AS retiring_12m_e7_plus,
    COUNT(DISTINCT sp.position_id) AS succession_plan_roles,
    STRING_AGG(DISTINCT IF(sp.position_id IS NOT NULL, CONCAT(sp.role_title, ' (', CAST(e.retirement_date AS STRING), ')'), NULL)) AS plan_roles_retiring,
    MIN(e.retirement_date) AS first_retirement
FROM employee_master e
JOIN dim_work_centre w ON e.current_wc_id = w.wc_id
JOIN dim_discipline d ON e.discipline_id = d.discipline_id
LEFT JOIN succession_plan sp ON sp.incumbent_emp_id = e.emp_id
WHERE LOWER(e.employment_status) = 'active'
  AND e.current_grade_id LIKE 'E%'
  AND e.current_wc_id IN ('WC-MUM', 'WC-NEH', 'WC-DRL')
  AND e.retirement_date BETWEEN DATE '2026-10-19' AND DATE '2027-10-18'
GROUP BY w.short_name, d.name
ORDER BY retiring_12m_e5_plus DESC, retiring_12m DESC, work_centre, discipline_name;
