-- Probe ID: C2.drill_down
-- Parent ID: C2
-- Answer Type: sql
-- Question: What is the discipline-wise deficit in Assam Asset (Nazira/Sivasagar) and Tripura Asset (Agartala) versus sanctioned posts?
-- Personas: CMD
-- Tables: sanctioned_posts, dim_work_centre, dim_discipline
-- Drill Dims: dim_work_centre.short_name, dim_discipline.name
-- Story IDs: S2
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc.short_name,
    d.name AS discipline_name,
    COUNT(DISTINCT e.emp_id) AS executive_count
FROM employee_master e
JOIN dim_work_centre wc ON e.current_wc_id = wc.wc_id
JOIN dim_discipline d ON e.discipline_id = d.discipline_id
WHERE wc.wc_id IN ('WC-ASM', 'WC-TRI')
  AND e.current_grade_id LIKE 'E%'
GROUP BY wc.short_name, d.name
ORDER BY wc.short_name, executive_count DESC;
