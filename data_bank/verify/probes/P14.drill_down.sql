-- Probe ID: P14.drill_down
-- Parent ID: P14
-- Answer Type: sql
-- Question: What are the target vs actual achievements for key MoU parameters?
-- Personas: Director (Finance)
-- Tables: mou_targets, payroll_monthly, dim_grade
-- Drill Dims: mou_targets.parameter_name
-- Story IDs: S27
-- Expected Output: table
-- Handcrafted: true

SELECT
    parameter_name,
    weightage,
    excellent_target,
    actual_achievement
FROM mou_targets
WHERE fiscal_year IN ('FY26', '2026')
ORDER BY parameter_name;
