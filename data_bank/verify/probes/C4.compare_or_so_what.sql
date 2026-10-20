-- Probe ID: C4.compare_or_so_what
-- Parent ID: C4
-- Answer Type: sql
-- Question: What percentage of eligible E6 Chief Engineers / Chief Geologists meet the DPC benchmark for accelerated promotion to GM?
-- Personas: CMD
-- Tables: dpc_cases, employee_master, dim_grade
-- Drill Dims: dpc_cases.status
-- Story IDs: S4
-- Expected Output: number
-- Handcrafted: true

SELECT
    d.status,
    d.from_grade_id,
    d.to_grade_id,
    COUNT(DISTINCT d.emp_id) AS dpc_candidates_count
FROM dpc_cases d
WHERE d.from_grade_id = 'E6' AND d.to_grade_id = 'E7'
GROUP BY d.status, d.from_grade_id, d.to_grade_id;
