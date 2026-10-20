-- Probe ID: F1.drill_down
-- Parent ID: F1
-- Answer Type: sql
-- Question: What are the individual cost components (power, workover, chemicals, surface repair, water handling) of lifting cost for the highest-cost asset?
-- Personas: Director (Finance)
-- Tables: field_pnl_annual, dim_work_centre
-- Drill Dims: dim_work_centre.short_name
-- Story IDs: S8
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc.short_name,
    SUM(pnl.power_fuel_cost_inr_cr) AS power_fuel_cr,
    SUM(pnl.workover_repairs_cost_inr_cr) AS workover_repairs_cr,
    SUM(pnl.water_handling_cost_inr_cr) AS water_handling_cr,
    SUM(pnl.chemicals_consumables_cost_inr_cr) AS chemicals_cr,
    SUM(pnl.total_opex_inr_cr) AS total_opex_cr
FROM field_pnl_annual pnl
JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
WHERE pnl.fiscal_year IN ('FY26', '2026')
GROUP BY wc.short_name
ORDER BY total_opex_cr DESC;
