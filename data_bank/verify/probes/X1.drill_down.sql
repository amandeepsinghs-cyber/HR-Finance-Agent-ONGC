-- Probe ID: X1.drill_down
-- Parent ID: X1
-- Answer Type: sql
-- Question: What is the ratio of contract workforce to regular employees at Hazira Plant, Uran Plant, and Mumbai High?
-- Personas: CMD, Director (HR)
-- Tables: contract_workforce, dim_work_centre
-- Drill Dims: dim_work_centre.short_name
-- Story IDs: S13
-- Expected Output: table
-- Handcrafted: false

SELECT
    dim_work_centre.short_name,
    AVG(contract_workforce.contractor_to_regular_ratio) AS metric_1
FROM contract_workforce
LEFT JOIN dim_work_centre ON contract_workforce.wc_id = dim_work_centre.wc_id
WHERE dim_work_centre.short_name IN ('Hazira Plant', 'Uran Plant', 'Mumbai High')
GROUP BY dim_work_centre.short_name
ORDER BY dim_work_centre.short_name
LIMIT 100;
