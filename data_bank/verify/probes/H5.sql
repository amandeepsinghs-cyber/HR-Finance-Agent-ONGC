-- Probe ID: H5
-- Parent ID: None
-- Answer Type: sql
-- Question: How many DPC (promotion) cases are pending, and for how long?
-- Personas: Director (HR)
-- Tables: dpc_cases, dim_grade
-- Drill Dims: dpc_cases.from_grade_id, dpc_cases.to_grade_id
-- Story IDs: S11
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 186.0 (total_pending_dpc_gt_6mo)
-- Expected Range: 167.4 - 204.6 (tolerance: ±10.0%)

SELECT
    from_grade_id,
    to_grade_id,
    COUNT(DISTINCT emp_id) AS pending_dpc_count
FROM dpc_cases
WHERE delay_months >= 6
GROUP BY from_grade_id, to_grade_id
ORDER BY from_grade_id;
