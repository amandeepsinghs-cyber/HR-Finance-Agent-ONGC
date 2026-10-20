-- Probe ID: H1
-- Parent ID: None
-- Answer Type: sql
-- Question: List the executives with more than 3 years at their current station (rotation policy), by asset and grade.
-- Personas: Director (HR)
-- Tables: posting_history, employee_master, dim_work_centre, dim_grade
-- Drill Dims: dim_work_centre.name, posting_history.grade_id
-- Story IDs: S38
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 5.0 (demo_personas_count)
-- Expected Range: 4.5 - 5.5 (tolerance: ±10.0%)

SELECT
    wc.name,
    p.grade_id,
    COUNT(DISTINCT p.emp_id) AS officer_count
FROM posting_history p
JOIN dim_work_centre wc ON p.wc_id = wc.wc_id
WHERE p.to_date IS NULL AND p.grade_id LIKE 'E%'
GROUP BY wc.name, p.grade_id
ORDER BY officer_count DESC
LIMIT 20;
