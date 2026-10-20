-- Answer Key Follow-up SQL: C5__why
-- Question: Why has low executive trainee recruitment between FY20 and FY25 exacerbated the mid-career seniority vacuum?
-- Type: data
-- Semantic audit 2026-10-20: old SQL listed FY21+ joiners in three disciplines with no baseline, so "low"
-- could not be judged. Now: executive intake (all entry modes, regardless of current status) per joining FY
-- FY14-FY26 for the core technical disciplines (Drilling, Geology, Geophysics, Reservoir, Production), the
-- number still active, and a window label (FY14-FY19 baseline vs FY20-FY25 question window vs FY26).

SELECT
    e.fiscal_year_joined,
    CASE WHEN e.fiscal_year_joined IN ('FY20', 'FY21', 'FY22', 'FY23', 'FY24', 'FY25') THEN 'FY20-FY25'
         WHEN e.fiscal_year_joined = 'FY26' THEN 'FY26'
         ELSE 'FY14-FY19' END AS period,
    COUNT(DISTINCT e.emp_id) AS technical_executive_intake,
    COUNT(DISTINCT IF(LOWER(e.employment_status) = 'active', e.emp_id, NULL)) AS still_active,
    COUNT(DISTINCT IF(e.discipline_id = 'DISC-DRL', e.emp_id, NULL)) AS drilling,
    COUNT(DISTINCT IF(e.discipline_id IN ('DISC-GEO', 'DISC-GPS', 'DISC-GPW'), e.emp_id, NULL)) AS geoscience,
    COUNT(DISTINCT IF(e.discipline_id = 'DISC-RES', e.emp_id, NULL)) AS reservoir,
    COUNT(DISTINCT IF(e.discipline_id = 'DISC-PRD', e.emp_id, NULL)) AS production
FROM employee_master e
WHERE e.discipline_id IN ('DISC-DRL', 'DISC-GEO', 'DISC-GPS', 'DISC-GPW', 'DISC-RES', 'DISC-PRD')
  AND e.fiscal_year_joined IN ('FY14', 'FY15', 'FY16', 'FY17', 'FY18', 'FY19', 'FY20', 'FY21', 'FY22', 'FY23', 'FY24', 'FY25', 'FY26')
  AND e.current_grade_id LIKE 'E%'
GROUP BY e.fiscal_year_joined, period
ORDER BY e.fiscal_year_joined;
