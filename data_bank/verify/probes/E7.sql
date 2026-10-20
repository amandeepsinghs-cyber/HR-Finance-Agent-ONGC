-- Probe ID: E7
-- Parent ID: None
-- Answer Type: sql
-- Question: What was ONGC's published annual profit last year? *(public data)*
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: corporate_financials
-- Drill Dims: 
-- Story IDs: S38
-- Expected Output: number
-- Handcrafted: false
-- Story Target: 5.0 (demo_personas_count)
-- Expected Range: 4.5 - 5.5 (tolerance: ±10.0%)

SELECT
    corporate_financials.pat_inr_cr AS pat_inr_cr
FROM corporate_financials
WHERE corporate_financials.fiscal_year IN ('FY26', '2026')
ORDER BY 1
LIMIT 100;
