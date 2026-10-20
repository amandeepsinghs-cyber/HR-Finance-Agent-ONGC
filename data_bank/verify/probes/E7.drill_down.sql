-- Probe ID: E7.drill_down
-- Parent ID: E7
-- Answer Type: sql
-- Question: What was the breakdown between standalone profit after tax (PAT) and consolidated group profit for FY25/FY26?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: corporate_financials
-- Drill Dims: corporate_financials.fiscal_year
-- Story IDs: S38
-- Expected Output: table
-- Handcrafted: false

SELECT
    corporate_financials.fiscal_year,
    corporate_financials.pat_inr_cr, corporate_financials.consolidated_pat_inr_cr AS consolidated_pat_inr_cr
FROM corporate_financials
WHERE corporate_financials.fiscal_year IN ('FY25', '2025', 'FY26', '2026')
ORDER BY corporate_financials.fiscal_year
LIMIT 100;
