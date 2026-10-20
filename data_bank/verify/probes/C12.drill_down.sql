-- Probe ID: C12.drill_down
-- Parent ID: C12
-- Answer Type: sql
-- Question: Break down the manpower cost per BOE for Mumbai High, Neelam-Heera, Ahmedabad, and Assam into executive vs non-executive payroll.
-- Personas: CMD
-- Tables: field_pnl_annual, dim_work_centre
-- Drill Dims: dim_work_centre.short_name
-- Story IDs: S8
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc.short_name,
    ROUND(AVG(pnl.manpower_cost_per_boe_usd), 2) AS manpower_cost_usd_boe,
    SUM(pnl.allocated_manpower_cost_inr_cr) AS total_manpower_cost_cr
FROM field_pnl_annual pnl
JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
WHERE wc.wc_id IN ('WC-MUM', 'WC-NEH', 'WC-AHM', 'WC-ASM')
  AND pnl.fiscal_year IN ('FY26', '2026')
GROUP BY wc.short_name
ORDER BY manpower_cost_usd_boe DESC;
