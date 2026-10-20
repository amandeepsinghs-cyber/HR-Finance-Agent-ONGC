-- Probe ID: F3.drill_down
-- Parent ID: F3
-- Answer Type: sql
-- Question: Which fields have demonstrated improving EBITDA margins despite natural decline in reservoir pressure?
-- Personas: Director (Finance)
-- Tables: field_pnl_annual, dim_field
-- Drill Dims: dim_field.name
-- Story IDs: S6
-- Expected Output: table
-- Handcrafted: true

SELECT
    f.name AS field_name,
    pnl.ebitda_inr_cr,
    ROUND((pnl.ebitda_inr_cr * 100.0) / NULLIF(pnl.gross_revenue_inr_cr, 0), 2) AS ebitda_margin_pct
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
WHERE pnl.fiscal_year IN ('FY26', '2026')
ORDER BY pnl.ebitda_inr_cr ASC;
