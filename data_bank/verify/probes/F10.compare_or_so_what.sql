-- Probe ID: F10.compare_or_so_what
-- Parent ID: F10
-- Answer Type: sql
-- Question: How does each asset's quarterly operating profit compare with the sanctioned annual operating plan (BE)?
-- Personas: Director (Finance)
-- Tables: field_pnl_annual, capex_budget, dim_work_centre
-- Drill Dims: dim_work_centre.name
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
