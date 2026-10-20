-- Probe ID: P12
-- Parent ID: None
-- Answer Type: sql_plus_rag
-- Question: Which executives are due for an E4→E5 merit review and have **not** done a North-East or hard posting?
-- Personas: Director (HR)
-- Tables: dpc_cases, employee_master, posting_history
-- Drill Dims: dpc_cases.discipline_id
-- Story IDs: S2
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 2120.0 (ne_executive_manpower_norm)
-- Expected Range: 1908.0 - 2332.0 (tolerance: ±10.0%)

WITH hard_station_officers AS (
    SELECT DISTINCT p.emp_id
    FROM posting_history p
    JOIN dim_work_centre wc ON p.wc_id = wc.wc_id
    WHERE wc.hard_station_cat = 'C'
)
SELECT
    d.discipline_id,
    COUNT(DISTINCT d.emp_id) AS metric_1
FROM dpc_cases d
WHERE d.from_grade_id = 'E4' AND d.to_grade_id = 'E5'
  AND d.emp_id NOT IN (SELECT emp_id FROM hard_station_officers)
GROUP BY d.discipline_id
ORDER BY d.discipline_id
LIMIT 100;
