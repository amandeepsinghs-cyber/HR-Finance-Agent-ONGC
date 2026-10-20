-- Probe ID: F3.compare_or_so_what
-- Parent ID: F3
-- Answer Type: sql
-- Question: How do 5-year cumulative revenues and operating cash flows compare between Western Offshore and Onshore Gujarat assets?
-- Personas: Director (Finance)
-- Tables: field_pnl_annual, dim_field
-- Drill Dims: dim_field.basin
-- Story IDs: S6
-- Expected Output: chart
-- Handcrafted: true

SELECT
    f.basin,
    SUM(pnl.gross_revenue_inr_cr) AS total_revenue_cr,
    SUM(pnl.ebitda_inr_cr) AS total_ebitda_cr
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
WHERE pnl.fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
GROUP BY f.basin
ORDER BY total_revenue_cr DESC;
