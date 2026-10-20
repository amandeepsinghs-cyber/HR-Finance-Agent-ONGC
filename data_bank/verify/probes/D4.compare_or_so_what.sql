-- Probe ID: D4.compare_or_so_what
-- Parent ID: D4
-- Answer Type: sql
-- Question: What were ONGC's total standalone capex spend and revenue reported in the last audited financial year?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: corporate_financials
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: table
-- Handcrafted: false

SELECT
    corporate_financials.gross_revenue_inr_cr, corporate_financials.total_capex_spent_inr_cr AS total_capex_spent_inr_cr
FROM corporate_financials
WHERE corporate_financials.fiscal_year IN ('FY26', '2026')
ORDER BY 1
LIMIT 100;
