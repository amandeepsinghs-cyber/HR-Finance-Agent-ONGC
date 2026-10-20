-- Probe ID: H2
-- Parent ID: None
-- Answer Type: sql_plus_rag
-- Question: Which employees have never served in a hard or remote station?
-- Personas: Director (HR)
-- Tables: employee_master, posting_history, dim_work_centre, dim_grade
-- Drill Dims: employee_master.current_grade_id
-- Story IDs: S2
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 2120.0 (ne_executive_manpower_norm)
-- Expected Range: 1908.0 - 2332.0 (tolerance: ±10.0%)

SELECT
    e.current_grade_id,
    COUNT(DISTINCT e.emp_id) AS in_position_executives
FROM employee_master e
JOIN dim_work_centre wc ON e.current_wc_id = wc.wc_id
WHERE wc.wc_id IN ('WC-ASM', 'WC-JOR', 'WC-TRI', 'WC-SIL')
  AND e.current_grade_id LIKE 'E%'
GROUP BY e.current_grade_id;
