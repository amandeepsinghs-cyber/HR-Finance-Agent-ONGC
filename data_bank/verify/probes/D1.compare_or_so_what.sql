-- Probe ID: D1.compare_or_so_what
-- Parent ID: D1
-- Answer Type: sql
-- Question: How does my own total compensation compare to the midpoint of the E2 pay scale band?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: payroll_monthly, dim_grade
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: number
-- Handcrafted: false

SELECT
    (dim_grade.pay_scale_min_inr + dim_grade.pay_scale_max_inr) / 2.0 AS metric_1
FROM payroll_monthly
LEFT JOIN dim_grade ON payroll_monthly.grade_id = dim_grade.grade_id
WHERE payroll_monthly.emp_id = 'EMP-102451' AND dim_grade.grade_id = 'E2'
ORDER BY 1
LIMIT 100;
