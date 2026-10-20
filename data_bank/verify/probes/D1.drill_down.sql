-- Probe ID: D1.drill_down
-- Parent ID: D1
-- Answer Type: sql
-- Question: What is the published pay scale and basic pay range for my reporting officer's grade (E6)?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: dim_grade
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: table
-- Handcrafted: false

SELECT
    dim_grade.pay_scale_min_inr, dim_grade.pay_scale_max_inr AS pay_scale_max_inr
FROM dim_grade
WHERE dim_grade.grade_id = 'E6'
ORDER BY 1
LIMIT 100;
