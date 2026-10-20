-- Probe ID: P12.drill_down
-- Parent ID: P12
-- Answer Type: sql
-- Question: How many of the 260 E4 executives awaiting E5 promotion consideration fall into Drilling, Production, and F&A?
-- Personas: Director (HR)
-- Tables: dpc_cases, employee_master, dim_discipline, posting_history
-- Drill Dims: dim_discipline.name
-- Story IDs: S2
-- Expected Output: table
-- Handcrafted: true

WITH hard_station_officers AS (
    SELECT DISTINCT p.emp_id
    FROM posting_history p
    JOIN dim_work_centre wc ON p.wc_id = wc.wc_id
    WHERE wc.hard_station_cat = 'C'
)
SELECT
    dim_discipline.name,
    COUNT(DISTINCT dpc_cases.emp_id) AS metric_1
FROM dpc_cases
JOIN dim_discipline ON dpc_cases.discipline_id = dim_discipline.discipline_id
WHERE dpc_cases.from_grade_id = 'E4' AND dpc_cases.to_grade_id = 'E5'
  AND dpc_cases.emp_id NOT IN (SELECT emp_id FROM hard_station_officers)
  AND dim_discipline.name IN ('Drilling', 'Production', 'Finance & Accounts (F&A)')
GROUP BY dim_discipline.name
ORDER BY dim_discipline.name
LIMIT 100;
