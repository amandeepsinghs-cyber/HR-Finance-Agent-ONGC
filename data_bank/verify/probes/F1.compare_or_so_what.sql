-- Probe ID: F1.compare_or_so_what
-- Parent ID: F1
-- Answer Type: sql
-- Question: How does the lifting cost of Mumbai High offshore compare with onshore assets and the overall company average ($11.5/BOE)?
-- Personas: Director (Finance)
-- Tables: field_pnl_annual, corporate_financials, dim_work_centre
-- Drill Dims: dim_work_centre.short_name
-- Story IDs: S8
-- Expected Output: chart
-- Handcrafted: true

SELECT
    wc.short_name,
    pnl.allocated_manpower_cost_inr_cr,
    ROUND((pnl.allocated_manpower_cost_inr_cr * 10000000.0) / NULLIF(pnl.gross_revenue_inr_cr * 10000000.0, 0) * 100.0, 2) AS manpower_cost_pct_revenue
FROM field_pnl_annual pnl
JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
WHERE pnl.fiscal_year IN ('FY26', '2026')
GROUP BY wc.short_name, pnl.allocated_manpower_cost_inr_cr, pnl.gross_revenue_inr_cr
ORDER BY manpower_cost_pct_revenue DESC;
