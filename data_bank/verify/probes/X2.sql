-- Probe ID: X2
-- Parent ID: None
-- Answer Type: sql
-- Question: Which assets rely most on contract labour for core operations?
-- Personas: Director (HR)
-- Tables: contract_workforce, dim_work_centre
-- Drill Dims: dim_work_centre.name
-- Story IDs: S13
-- Expected Output: table
-- Handcrafted: false
-- Story Target: 1120.0 (hazira_regular_headcount)
-- Expected Range: 1008.0 - 1232.0 (tolerance: ±10.0%)

SELECT
    dim_work_centre.name,
    SUM(contract_workforce.contractor_headcount) AS metric_1
FROM contract_workforce
LEFT JOIN dim_work_centre ON contract_workforce.wc_id = dim_work_centre.wc_id
WHERE contract_workforce.is_core_activity = TRUE
GROUP BY dim_work_centre.name
ORDER BY dim_work_centre.name
LIMIT 100;
