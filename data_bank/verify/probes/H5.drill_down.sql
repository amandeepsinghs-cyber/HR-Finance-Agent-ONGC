-- Probe ID: H5.drill_down
-- Parent ID: H5
-- Answer Type: sql
-- Question: Which specific grades (e.g. E4 to E5, E5 to E6) and disciplines have DPC meetings delayed beyond 6 months?
-- Personas: Director (HR)
-- Tables: dpc_cases, dim_discipline
-- Drill Dims: dpc_cases.from_grade_id, dim_discipline.name
-- Story IDs: S11
-- Expected Output: table
-- Handcrafted: true

SELECT
    d.from_grade_id,
    disc.name,
    COUNT(DISTINCT d.emp_id) AS pending_dpc_count
FROM dpc_cases d
JOIN dim_discipline disc ON d.discipline_id = disc.discipline_id
WHERE d.delay_months >= 6
GROUP BY d.from_grade_id, disc.name
ORDER BY d.from_grade_id;
