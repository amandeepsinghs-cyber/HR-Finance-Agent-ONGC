-- Probe ID: T3
-- Parent ID: None
-- Answer Type: sql_plus_rag
-- Question: "Which GMs retire in 2027?" → "Who is ready to succeed each?" → "Which successors haven't served in the North East?"
-- Personas: CMD, Director (HR)
-- Tables: employee_master, succession_plan, posting_history, dpc_cases
-- Drill Dims: succession_plan.position_id
-- Story IDs: S4
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 1142.0 (total_e7_plus_in_position)
-- Expected Range: 1027.8 - 1256.2 (tolerance: ±10.0%)

SELECT
    sp.position_id,
    sp.role_title,
    sp.incumbent_emp_id,
    sp.incumbent_retire_date,
    sp.successor_1_emp_id,
    sp.successor_1_readiness,
    sp.successor_1_has_ne_hard_station
FROM succession_plan sp
WHERE sp.incumbent_retire_date BETWEEN DATE '2026-10-19' AND DATE '2027-12-31'
ORDER BY sp.position_id;
