-- Probe ID: M3.compare_or_so_what
-- Parent ID: M3
-- Answer Type: sql
-- Question: What is the designated salary pay scale and promotion criteria for employee 104523's grade?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: dim_grade
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: table
-- Handcrafted: false

SELECT
    dim_grade.pay_scale_min_inr, dim_grade.pay_scale_max_inr AS pay_scale_max_inr
FROM dim_grade
WHERE dim_grade.grade_id = 'E3'
ORDER BY 1
LIMIT 100;
