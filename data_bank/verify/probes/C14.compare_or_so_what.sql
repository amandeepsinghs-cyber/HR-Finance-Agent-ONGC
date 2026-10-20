-- Probe ID: C14.compare_or_so_what
-- Parent ID: C14
-- Answer Type: sql
-- Question: What is the quantified financial payoff of farm-out/PEC versus continued in-house operation over a 5-year outlook?
-- Personas: CMD
-- Tables: field_pnl_annual, dim_field
-- Drill Dims: dim_field.name
-- Story IDs: S6
-- Expected Output: table
-- Handcrafted: true

SELECT
    f.name AS field_name,
    pnl.ebitda_inr_cr
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
WHERE pnl.fiscal_year IN ('FY26', '2026')
ORDER BY pnl.ebitda_inr_cr ASC;
