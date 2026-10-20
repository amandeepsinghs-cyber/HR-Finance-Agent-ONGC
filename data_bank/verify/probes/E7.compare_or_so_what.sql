-- Probe ID: E7.compare_or_so_what
-- Parent ID: E7
-- Answer Type: sql
-- Question: How does last year's net profit compare with the previous 3-year average annual earnings?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: corporate_financials
-- Drill Dims: corporate_financials.fiscal_year
-- Story IDs: S38
-- Expected Output: chart
-- Handcrafted: false

SELECT
    corporate_financials.fiscal_year,
    AVG(corporate_financials.pat_inr_cr) AS metric_1
FROM corporate_financials
WHERE corporate_financials.fiscal_year IN ('FY23', '2023', 'FY24', '2024', 'FY25', '2025', 'FY26', '2026')
GROUP BY corporate_financials.fiscal_year
ORDER BY corporate_financials.fiscal_year
LIMIT 100;
