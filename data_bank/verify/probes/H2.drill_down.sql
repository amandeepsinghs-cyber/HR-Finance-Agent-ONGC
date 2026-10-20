-- Probe ID: H2.drill_down
-- Parent ID: H2
-- Answer Type: sql
-- Question: Filter the list for E4–E5 executives who are currently within the zone of consideration for promotion to E5/E6.
-- Personas: Director (HR)
-- Tables: employee_master, dpc_cases
-- Drill Dims: employee_master.current_grade_id
-- Story IDs: S2
-- Expected Output: list
-- Handcrafted: true

SELECT
    e.current_grade_id,
    COUNT(DISTINCT d.emp_id) AS candidates_count
FROM dpc_cases d
JOIN employee_master e ON d.emp_id = e.emp_id
WHERE e.current_wc_id IN ('WC-ASM', 'WC-JOR', 'WC-TRI', 'WC-SIL')
GROUP BY e.current_grade_id;
