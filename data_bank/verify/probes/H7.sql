-- Probe ID: H7
-- Parent ID: None
-- Answer Type: sql
-- Question: What is women's representation by grade and asset, and what has it been for offshore postings?
-- Personas: Director (HR)
-- Tables: employee_master, posting_history, dim_grade, dim_work_centre
-- Drill Dims: employee_master.current_grade_id, dim_work_centre.name
-- Story IDs: S17
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 1885.0 (total_female_headcount)
-- Expected Range: 1696.5 - 2073.5 (tolerance: ±10.0%)

SELECT
    e.current_grade_id,
    wc.name,
    COUNT(DISTINCT e.emp_id) AS women_executive_count
FROM employee_master e
JOIN dim_work_centre wc ON e.current_wc_id = wc.wc_id
WHERE e.gender = 'Female'
  AND e.current_grade_id LIKE 'E%'
  AND e.employment_status = 'Active'
GROUP BY e.current_grade_id, wc.name
ORDER BY women_executive_count DESC
LIMIT 20;
