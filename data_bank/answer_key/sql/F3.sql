-- Answer Key SQL: F3
-- Question: What is the revenue, opex and EBITDA for each field over 5 years?
-- Type: data

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
