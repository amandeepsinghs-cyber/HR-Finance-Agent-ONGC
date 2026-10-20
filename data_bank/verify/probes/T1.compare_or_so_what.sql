-- Probe ID: T1.compare_or_so_what
-- Parent ID: T1
-- Answer Type: sql
-- Question: What is the net cost impact of divesting Field X versus investing in secondary recovery over a 5-year horizon?
-- Personas: CMD, Director (Finance)
-- Tables: field_pnl_annual, dim_field
-- Drill Dims: 
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
