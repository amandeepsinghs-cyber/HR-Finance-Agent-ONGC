-- Probe ID: X2.drill_down
-- Parent ID: X2
-- Answer Type: sql
-- Question: Which production installations in Gujarat and Assam employ contract personnel in drilling or hydrocarbon processing roles?
-- Personas: Director (HR)
-- Tables: contract_workforce, dim_work_centre, dim_discipline
-- Drill Dims: dim_work_centre.state, dim_discipline.name
-- Story IDs: S13
-- Expected Output: table
-- Handcrafted: false

SELECT
    dim_work_centre.state,
    dim_discipline.name,
    SUM(contract_workforce.contractor_headcount) AS metric_1
FROM contract_workforce
LEFT JOIN dim_work_centre ON contract_workforce.wc_id = dim_work_centre.wc_id
LEFT JOIN dim_discipline ON contract_workforce.discipline_id = dim_discipline.discipline_id
WHERE dim_work_centre.state IN ('Gujarat', 'Assam') AND contract_workforce.is_core_activity = TRUE
GROUP BY dim_work_centre.state, dim_discipline.name
ORDER BY dim_work_centre.state
LIMIT 100;
