-- Probe ID: C5.why
-- Parent ID: C5
-- Answer Type: sql_plus_rag
-- Question: Why has low executive trainee recruitment between FY20 and FY25 exacerbated the mid-career seniority vacuum?
-- Personas: CMD
-- Tables: employee_master, dim_discipline
-- Drill Dims: employee_master.fiscal_year_joined, employee_master.discipline_id
-- Story IDs: S5
-- Expected Output: table
-- Handcrafted: true

SELECT
    e.fiscal_year_joined,
    e.discipline_id,
    COUNT(DISTINCT e.emp_id) AS recent_intake_count
FROM employee_master e
WHERE e.discipline_id IN ('DISC-DRL', 'DISC-GEO', 'DISC-GPS')
  AND e.doj >= DATE '2020-04-01'
GROUP BY e.fiscal_year_joined, e.discipline_id
ORDER BY e.fiscal_year_joined, e.discipline_id;
