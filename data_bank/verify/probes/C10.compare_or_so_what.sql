-- Probe ID: C10.compare_or_so_what
-- Parent ID: C10
-- Answer Type: sql
-- Question: How does our projected FY27 MoU composite score compare with our FY26 Excellent rating?
-- Personas: CMD
-- Tables: mou_targets
-- Drill Dims: mou_targets.fiscal_year
-- Story IDs: S10
-- Expected Output: table
-- Handcrafted: true

SELECT
    fiscal_year,
    COUNT(*) AS total_parameters_tracked,
    SUM(weightage) AS total_weightage
FROM mou_targets
GROUP BY fiscal_year
ORDER BY fiscal_year;
