-- Probe ID: C10.drill_down
-- Parent ID: C10
-- Answer Type: sql
-- Question: What are the specific MoU parameter scores for crude production, gas production, and capex execution?
-- Personas: CMD
-- Tables: mou_targets
-- Drill Dims: mou_targets.parameter_name
-- Story IDs: S10
-- Expected Output: table
-- Handcrafted: true

SELECT
    parameter_name,
    weightage,
    excellent_target,
    actual_achievement
FROM mou_targets
WHERE fiscal_year IN ('FY26', '2026')
ORDER BY weightage DESC;
