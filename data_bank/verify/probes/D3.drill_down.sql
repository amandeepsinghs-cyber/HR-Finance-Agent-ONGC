-- Probe ID: D3.drill_down
-- Parent ID: D3
-- Answer Type: sql
-- Question: Which grades and disciplines are being considered in the current DPC cycle?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: dpc_cases
-- Drill Dims: dpc_cases.from_grade_id, dpc_cases.to_grade_id
-- Story IDs: 
-- Expected Output: table
-- Handcrafted: true

SELECT
    from_grade_id,
    to_grade_id,
    COUNT(DISTINCT emp_id) AS dpc_candidates
FROM dpc_cases
GROUP BY from_grade_id, to_grade_id
ORDER BY from_grade_id;
