-- Probe ID: P14.compare_or_so_what
-- Parent ID: P14
-- Answer Type: sql
-- Question: How does our overall MoU score compare with past years?
-- Personas: Director (Finance)
-- Tables: mou_targets, payroll_monthly
-- Drill Dims: mou_targets.parameter_name
-- Story IDs: S27
-- Expected Output: table
-- Handcrafted: true

SELECT
    parameter_name,
    actual_achievement,
    excellent_target
FROM mou_targets
WHERE fiscal_year IN ('FY26', '2026')
ORDER BY parameter_name;
