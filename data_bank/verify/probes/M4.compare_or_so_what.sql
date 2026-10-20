-- Probe ID: M4.compare_or_so_what
-- Parent ID: M4
-- Answer Type: sql
-- Question: What was the total operating profit (EBITDA) reported by ONGC in the last audited annual financial statements?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: corporate_financials
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: number
-- Handcrafted: false

SELECT
    corporate_financials.ebitda_inr_cr AS ebitda_inr_cr
FROM corporate_financials
WHERE corporate_financials.fiscal_year IN ('FY26', '2026')
ORDER BY 1
LIMIT 100;
