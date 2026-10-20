-- Probe ID: F6.compare_or_so_what
-- Parent ID: F6
-- Answer Type: sql
-- Question: How does our Days Sales Outstanding (DSO) compare with historical averages and treasury working capital targets?
-- Personas: Director (Finance)
-- Tables: receivables, corporate_financials
-- Drill Dims: 
-- Story IDs: S23
-- Expected Output: number
-- Handcrafted: false

SELECT
    (SUM(receivables.outstanding_amount_inr_cr) * 365.0) / NULLIF(SUM(corporate_financials.gross_revenue_inr_cr), 0) AS metric_1
FROM receivables
LEFT JOIN corporate_financials ON corporate_financials.fiscal_year = receivables.fiscal_year
WHERE receivables.fiscal_year IN ('FY26', '2026')
ORDER BY 1
LIMIT 100;
