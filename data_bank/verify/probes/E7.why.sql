-- Probe ID: E7.why
-- Parent ID: E7
-- Answer Type: sql
-- Question: What major factors (crude realization, statutory cess, dividend income) drove the annual profit growth?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: corporate_financials
-- Drill Dims: 
-- Story IDs: S38
-- Expected Output: table
-- Handcrafted: false

SELECT
    corporate_financials.gross_revenue_inr_cr - corporate_financials.statutory_levies_total_inr_cr AS statutory_levies_total_inr_cr
FROM corporate_financials
WHERE corporate_financials.fiscal_year IN ('FY26', '2026')
ORDER BY 1
LIMIT 100;
