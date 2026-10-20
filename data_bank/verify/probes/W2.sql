-- Probe ID: W2
-- Parent ID: None
-- Answer Type: what_if_sim
-- Question: If we freeze hiring for 2 years, what will headcount be by discipline in 2028, given retirements?
-- Personas: CMD, Director (HR)
-- Tables: employee_master, separations, dim_discipline
-- Drill Dims: dim_discipline.name
-- Story IDs: S5
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 6420.0 (core_technical_executives_fy26)
-- Expected Range: 5778.0 - 7062.0 (tolerance: ±10.0%)

SELECT
    d.discipline_id,
    d.name AS discipline_name,
    COUNT(DISTINCT e.emp_id) AS in_position_fy26,
    COUNT(DISTINCT CASE WHEN e.dob <= DATE '1970-03-31' THEN e.emp_id END) AS retiring_by_2030,
    ROUND(COUNT(DISTINCT CASE WHEN e.dob <= DATE '1970-03-31' THEN e.emp_id END) * 100.0 / NULLIF(COUNT(DISTINCT e.emp_id), 0), 2) AS retirement_pct
FROM employee_master e
JOIN dim_discipline d ON e.discipline_id = d.discipline_id
WHERE e.current_grade_id LIKE 'E%'
  AND d.discipline_id IN ('DISC-DRL', 'DISC-GEO', 'DISC-GPS', 'DISC-RES', 'DISC-PRD')
  AND (e.employment_status = 'Active' OR e.separation_date IS NULL)
GROUP BY d.discipline_id, d.name
ORDER BY retiring_by_2030 DESC;
