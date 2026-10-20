-- Probe ID: C10
-- Parent ID: None
-- Answer Type: sql
-- Question: How are we tracking against our MoU targets with MoPNG/DPE for this year?
-- Personas: CMD
-- Tables: mou_targets, production_monthly, capex_budget
-- Drill Dims: mou_targets.parameter_name
-- Story IDs: S10
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 10.15 (mou_crude_target_h1_mmt)
-- Expected Range: 9.13 - 11.17 (tolerance: ±10.0%)

SELECT
    parameter_name,
    weightage,
    excellent_target,
    actual_achievement,
    ROUND((actual_achievement * 100.0) / NULLIF(excellent_target, 0), 2) AS achievement_pct
FROM mou_targets
WHERE fiscal_year IN ('FY26', '2026')
ORDER BY weightage DESC;
