-- Probe ID: C14
-- Parent ID: None
-- Answer Type: document_gen
-- Question: Prepare a one-page board note on the top 5 loss-making fields: production, cost, staffing and a recommendation.
-- Personas: CMD
-- Tables: field_pnl_annual, production_monthly, headcount_snapshot, dim_field
-- Drill Dims: dim_field.name
-- Story IDs: S6
-- Expected Output: document
-- Handcrafted: true
-- Story Target: 0.042 (borholla_oil_production_mmt)
-- Expected Range: 0.04 - 0.05 (tolerance: ±10.0%)

SELECT
    f.name AS field_name,
    pnl.gross_revenue_inr_cr,
    pnl.total_opex_inr_cr,
    pnl.ebitda_inr_cr,
    pnl.pbt_inr_cr
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
WHERE pnl.fiscal_year IN ('FY26', '2026')
ORDER BY pnl.pbt_inr_cr ASC
LIMIT 5;
