-- Probe ID: F1
-- Parent ID: None
-- Answer Type: sql
-- Question: What is the lifting cost ($/bbl) by asset, and which assets are above the company average?
-- Personas: Director (Finance)
-- Tables: field_pnl_annual, dim_field, dim_work_centre, corporate_financials
-- Drill Dims: dim_work_centre.name
-- Story IDs: S8
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 358.4 (company_avg_employee_cost_per_boe)
-- Expected Range: 322.56 - 394.24 (tolerance: ±10.0%)

SELECT
    wc.short_name,
    pnl.allocated_manpower_cost_inr_cr,
    ROUND((pnl.allocated_manpower_cost_inr_cr * 10000000.0) / NULLIF(pnl.gross_revenue_inr_cr * 10000000.0, 0) * 100.0, 2) AS manpower_cost_pct_revenue
FROM field_pnl_annual pnl
JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
WHERE pnl.fiscal_year IN ('FY26', '2026')
GROUP BY wc.short_name, pnl.allocated_manpower_cost_inr_cr, pnl.gross_revenue_inr_cr
ORDER BY manpower_cost_pct_revenue DESC;
