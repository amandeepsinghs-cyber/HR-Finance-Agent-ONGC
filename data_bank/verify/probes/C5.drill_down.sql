-- Probe ID: C5.drill_down
-- Parent ID: C5
-- Answer Type: sql
-- Question: What is the projected cumulative superannuation count in Geology, Geophysics, and Reservoir Engineering by FY30?
-- Personas: CMD
-- Tables: employee_master, dim_discipline
-- Drill Dims: dim_discipline.name, employee_master.dob
-- Story IDs: S5
-- Expected Output: chart
-- Handcrafted: true

SELECT
    d.name,
    e.dob,
    COUNT(DISTINCT e.emp_id) AS retiring_count
FROM employee_master e
JOIN dim_discipline d ON e.discipline_id = d.discipline_id
WHERE d.discipline_id IN ('DISC-GEO', 'DISC-GPS', 'DISC-RES')
  AND e.current_grade_id LIKE 'E%'
  AND e.dob <= DATE '1970-03-31'
  AND (e.employment_status = 'Active' OR e.separation_date IS NULL)
GROUP BY d.name, e.dob
ORDER BY d.name, e.dob;
