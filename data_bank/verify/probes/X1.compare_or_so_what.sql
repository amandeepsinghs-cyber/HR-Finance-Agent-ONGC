-- Probe ID: X1.compare_or_so_what
-- Parent ID: X1
-- Answer Type: sql
-- Question: How does the contractor cost per BOE compare with regular employee cost across onshore and offshore assets?
-- Personas: CMD, Director (HR)
-- Tables: contract_workforce, field_pnl_annual, dim_work_centre
-- Drill Dims: dim_work_centre.name
-- Story IDs: S13
-- Expected Output: chart
-- Handcrafted: false

SELECT
    dim_work_centre.name,
    AVG(contract_workforce.contractor_cost_per_boe_usd) AS metric_1,
    AVG(field_pnl_annual.manpower_cost_per_boe_usd) AS metric_2
FROM contract_workforce
LEFT JOIN field_pnl_annual ON contract_workforce.wc_id = field_pnl_annual.asset_wc_id
LEFT JOIN dim_work_centre ON contract_workforce.wc_id = dim_work_centre.wc_id
WHERE contract_workforce.fiscal_year IN ('FY26', '2026')
GROUP BY dim_work_centre.name
ORDER BY dim_work_centre.name
LIMIT 100;
