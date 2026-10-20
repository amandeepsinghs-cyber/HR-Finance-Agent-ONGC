-- Probe ID: T1.drill_down
-- Parent ID: T1
-- Answer Type: sql
-- Question: Which specific offshore and onshore mature fields recorded negative operating earnings in FY26?
-- Personas: CMD, Director (Finance)
-- Tables: field_pnl_annual, dim_field
-- Drill Dims: dim_field.name, dim_field.onshore_offshore
-- Story IDs: S6
-- Expected Output: table
-- Handcrafted: true

SELECT
    f.name AS field_name,
    f.onshore_offshore,
    pnl.ebitda_inr_cr,
    pnl.pbt_inr_cr
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
WHERE pnl.fiscal_year IN ('FY26', '2026')
  AND (pnl.pbt_inr_cr < 0 OR pnl.ebitda_inr_cr < 0)
ORDER BY pnl.pbt_inr_cr ASC;
