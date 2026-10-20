-- Probe ID: C6
-- Parent ID: None
-- Answer Type: sql
-- Question: Which fields or assets were the most profitable and which made losses in FY26?
-- Personas: CMD
-- Tables: field_pnl_annual, dim_field, dim_work_centre
-- Drill Dims: dim_field.name, dim_work_centre.name
-- Story IDs: S6
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 0.042 (borholla_oil_production_mmt)
-- Expected Range: 0.04 - 0.05 (tolerance: ±10.0%)

SELECT
    f.name AS field_name,
    wc.name AS work_centre_name,
    pnl.fiscal_year,
    pnl.gross_revenue_inr_cr,
    pnl.total_opex_inr_cr,
    pnl.ebitda_inr_cr,
    pnl.pbt_inr_cr
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
WHERE pnl.fiscal_year IN ('FY26', '2026')
ORDER BY pnl.pbt_inr_cr DESC;
