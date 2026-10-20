-- Probe ID: P14
-- Parent ID: None
-- Answer Type: sql_plus_rag
-- Question: Our MoU rating sets the performance-related pay pool. What's the pay impact if we drop from "Excellent" to "Very Good"?
-- Personas: CMD, Director (Finance)
-- Tables: mou_targets, payroll_monthly
-- Drill Dims: mou_targets.achieved_rating
-- Story IDs: S27
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 1200.0 (prp_pool_excellent_cr)
-- Expected Range: 1080.0 - 1320.0 (tolerance: ±10.0%)

SELECT
    fiscal_year,
    parameter_name,
    achieved_rating,
    excellent_target,
    actual_achievement
FROM mou_targets
WHERE fiscal_year IN ('FY26', '2026')
ORDER BY weightage DESC;
