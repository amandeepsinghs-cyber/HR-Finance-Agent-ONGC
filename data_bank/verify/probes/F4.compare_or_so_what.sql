-- Probe ID: F4.compare_or_so_what
-- Parent ID: F4
-- Answer Type: sql
-- Question: How does the statutory government take percentage on ONGC nomination fields compare with NELP/HELP revenue-sharing contracts?
-- Personas: Director (Finance)
-- Tables: corporate_financials
-- Drill Dims: corporate_financials.fiscal_year
-- Story IDs: S21
-- Expected Output: number
-- Handcrafted: false

SELECT
    corporate_financials.fiscal_year,
    corporate_financials.statutory_levies_total_inr_cr * 100.0 / corporate_financials.gross_revenue_inr_cr AS gross_revenue_inr_cr
FROM corporate_financials
WHERE corporate_financials.fiscal_year IN ('FY26', '2026')
ORDER BY corporate_financials.fiscal_year
LIMIT 100;
