-- Probe ID: C5.compare_or_so_what
-- Parent ID: C5
-- Answer Type: sql
-- Question: How does our projected technical specialist loss compare with planned deepwater and HP-HT exploration projects?
-- Personas: CMD
-- Tables: employee_master, dim_discipline
-- Drill Dims: dim_discipline.name
-- Story IDs: S5
-- Expected Output: table
-- Handcrafted: true

SELECT
    dim_discipline.name,
    COUNT(DISTINCT CASE WHEN datediff('year', employee_master.dob, DATE '2030-03-31') >= 60 THEN employee_master.emp_id END) AS metric_1
FROM employee_master
JOIN dim_discipline ON employee_master.discipline_id = dim_discipline.discipline_id
WHERE LOWER(dim_discipline.function) = 'technical'
GROUP BY dim_discipline.name
ORDER BY dim_discipline.name
LIMIT 100;
