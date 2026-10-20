-- Probe ID: X2.compare_or_so_what
-- Parent ID: X2
-- Answer Type: sql
-- Question: How does core contract labour dependency compare between offshore production platforms and corporate office complexes?
-- Personas: Director (HR)
-- Tables: contract_workforce, dim_work_centre
-- Drill Dims: dim_work_centre.type
-- Story IDs: S13
-- Expected Output: chart
-- Handcrafted: false

SELECT
    dim_work_centre.type,
    SUM(contract_workforce.contractor_headcount) AS metric_1
FROM contract_workforce
LEFT JOIN dim_work_centre ON contract_workforce.wc_id = dim_work_centre.wc_id
WHERE contract_workforce.is_core_activity = TRUE
GROUP BY dim_work_centre.type
ORDER BY dim_work_centre.type
LIMIT 100;
