-- Probe ID: F3
-- Parent ID: None
-- Answer Type: sql
-- Question: What is the revenue, opex and EBITDA for each field over 5 years?
-- Personas: Director (Finance)
-- Tables: field_pnl_annual, dim_field
-- Drill Dims: dim_field.name, field_pnl_annual.fiscal_year
-- Story IDs: S6
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 0.042 (borholla_oil_production_mmt)
-- Expected Range: 0.04 - 0.05 (tolerance: ±10.0%)

SELECT
    f.name AS field_name,
    pnl.fiscal_year,
    pnl.gross_revenue_inr_cr,
    pnl.total_opex_inr_cr,
    pnl.ebitda_inr_cr,
    pnl.pbt_inr_cr
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
WHERE pnl.fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
ORDER BY f.name, pnl.fiscal_year;
