-- Probe ID: W2.why
-- Parent ID: W2
-- Answer Type: what_if_sim
-- Question: Why does the projected retirement cliff disproportionately deplete executive technical talent in senior grades?
-- Personas: CMD, Director (HR)
-- Tables: employee_master, dim_grade
-- Drill Dims: dim_grade.group
-- Story IDs: S5
-- Expected Output: table
-- Handcrafted: true

SELECT
    gr.group,
    COUNT(DISTINCT e.emp_id) AS retiring_count
FROM employee_master e
JOIN dim_grade gr ON e.current_grade_id = gr.grade_id
WHERE e.current_grade_id LIKE 'E%'
  AND e.dob <= DATE '1970-03-31'
GROUP BY gr.group;
