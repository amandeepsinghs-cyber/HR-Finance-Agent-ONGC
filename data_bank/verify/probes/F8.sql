-- Probe ID: F8
-- Parent ID: None
-- Answer Type: sql
-- Question: What is the finding & development cost and reserve replacement ratio, by basin?
-- Personas: Director (Finance)
-- Tables: reserves_annual, wells_drilled, capex_budget
-- Drill Dims: reserves_annual.basin_name
-- Story IDs: S24
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 1.17 (reserve_replacement_ratio_2p)
-- Expected Range: 1.05 - 1.29 (tolerance: ±10.0%)

SELECT
    r.basin_name,
    AVG(r.finding_cost_usd_per_boe) AS avg_finding_cost,
    AVG(r.development_cost_usd_per_boe) AS avg_dev_cost,
    ROUND(AVG(r.reserve_replacement_ratio_rrr_2p), 2) AS avg_rrr
FROM reserves_annual r
WHERE r.fiscal_year IN ('FY26', '2026')
GROUP BY r.basin_name
ORDER BY r.basin_name;
