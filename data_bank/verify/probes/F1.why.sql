-- Probe ID: F1.why
-- Parent ID: F1
-- Answer Type: sql
-- Question: Why has the lifting cost in mature fields like Cambay and Mehsana increased over the last 3 fiscal years?
-- Personas: Director (Finance)
-- Tables: field_pnl_annual, production_monthly, dim_work_centre
-- Drill Dims: dim_work_centre.short_name, field_pnl_annual.fiscal_year
-- Story IDs: S8
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc.short_name,
    pnl.fiscal_year,
    ROUND(AVG(pnl.lifting_cost_per_boe_usd), 2) AS lifting_cost_usd_boe,
    SUM(pnl.total_opex_inr_cr) AS total_opex_cr
FROM field_pnl_annual pnl
JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
WHERE wc.wc_id IN ('WC-CAM', 'WC-MEH')
  AND pnl.fiscal_year IN ('FY24', 'FY25', 'FY26')
GROUP BY wc.short_name, pnl.fiscal_year
ORDER BY wc.short_name, pnl.fiscal_year;
