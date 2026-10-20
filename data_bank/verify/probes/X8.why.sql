-- Probe ID: X8.why
-- Parent ID: X8
-- Answer Type: sql
-- Question: What procedural bottlenecks or documentation delays have prevented closure of audit paras aged over 3 years?
-- Personas: CMD
-- Tables: cag_paras
-- Drill Dims: cag_paras.bottleneck_reason
-- Story IDs: S19
-- Expected Output: table
-- Handcrafted: false

SELECT
    cag_paras.bottleneck_reason,
    COUNT(cag_paras.cag_para_id) AS metric_1
FROM cag_paras
WHERE cag_paras.is_aged_over_3_years = TRUE
GROUP BY cag_paras.bottleneck_reason
ORDER BY cag_paras.bottleneck_reason
LIMIT 100;
