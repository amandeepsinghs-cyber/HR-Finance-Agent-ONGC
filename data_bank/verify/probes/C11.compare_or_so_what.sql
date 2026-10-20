-- Probe ID: C11.compare_or_so_what
-- Parent ID: C11
-- Answer Type: sql
-- Question: How does the labor productivity (BOE per employee) in expanding assets compare with the ONGC corporate average?
-- Personas: CMD
-- Tables: field_pnl_annual, dim_work_centre
-- Drill Dims: dim_work_centre.name
-- Story IDs: S7
-- Expected Output: chart
-- Handcrafted: true

SELECT
    wc.name,
    ROUND(AVG(pnl.boe_per_employee), 1) AS avg_boe_per_employee,
    ROUND(AVG(pnl.manpower_cost_per_boe_usd), 2) AS avg_manpower_cost_usd_boe
FROM field_pnl_annual pnl
JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
WHERE pnl.fiscal_year IN ('FY26', '2026')
GROUP BY wc.name
ORDER BY avg_boe_per_employee DESC;
