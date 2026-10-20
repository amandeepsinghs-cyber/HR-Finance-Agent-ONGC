-- Probe ID: X1
-- Parent ID: None
-- Answer Type: sql
-- Question: How many contract workers vs. regular employees per asset, and at what cost per BOE?
-- Personas: CMD, Director (HR)
-- Tables: contract_workforce, headcount_snapshot, field_pnl_annual, dim_work_centre
-- Drill Dims: dim_work_centre.name
-- Story IDs: S13
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 1120.0 (hazira_regular_headcount)
-- Expected Range: 1008.0 - 1232.0 (tolerance: ±10.0%)

SELECT
    dim_work_centre.name,
    SUM(contract_workforce.contractor_headcount) AS metric_1,
    COALESCE(MAX(hs.reg_headcount), 0) AS metric_2,
    AVG(contract_workforce.contractor_cost_per_boe_usd) AS metric_3
FROM contract_workforce
LEFT JOIN (
    SELECT fiscal_year, wc_id, SUM(headcount) AS reg_headcount
    FROM headcount_snapshot
    GROUP BY fiscal_year, wc_id
) hs ON contract_workforce.fiscal_year = hs.fiscal_year AND contract_workforce.wc_id = hs.wc_id
LEFT JOIN dim_work_centre ON contract_workforce.wc_id = dim_work_centre.wc_id
WHERE contract_workforce.fiscal_year IN ('FY26', '2026')
GROUP BY dim_work_centre.name
ORDER BY dim_work_centre.name
LIMIT 100;
