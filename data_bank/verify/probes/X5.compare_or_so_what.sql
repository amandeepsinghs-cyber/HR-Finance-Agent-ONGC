-- Probe ID: X5.compare_or_so_what
-- Parent ID: X5
-- Answer Type: sql
-- Question: How has group consolidated net profit trended relative to ONGC standalone profit over 5 years?
-- Personas: Director (Finance)
-- Tables: subsidiary_financials
-- Drill Dims: subsidiary_financials.fiscal_year
-- Story IDs: S33
-- Expected Output: table
-- Handcrafted: true

SELECT
    fiscal_year,
    SUM(pat_inr_cr) AS total_subsidiary_pat_cr
FROM subsidiary_financials
GROUP BY fiscal_year
ORDER BY fiscal_year;
