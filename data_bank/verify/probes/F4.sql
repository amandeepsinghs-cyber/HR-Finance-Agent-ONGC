-- Probe ID: F4
-- Parent ID: None
-- Answer Type: sql
-- Question: How much did royalty, cess and windfall tax reduce realisation per barrel this year?
-- Personas: Director (Finance)
-- Tables: corporate_financials, price_fx_monthly
-- Drill Dims: corporate_financials.fiscal_year
-- Story IDs: S21
-- Expected Output: table
-- Handcrafted: false
-- Story Target: 13034.0 (oidb_cess_fy26_cr)
-- Expected Range: 11730.6 - 14337.4 (tolerance: ±10.0%)

SELECT
    corporate_financials.fiscal_year,
    SUM(corporate_financials.statutory_levies_total_inr_cr) AS metric_1
FROM corporate_financials
LEFT JOIN price_fx_monthly ON corporate_financials.fiscal_year = price_fx_monthly.fiscal_year
WHERE corporate_financials.fiscal_year IN ('FY26', '2026')
GROUP BY corporate_financials.fiscal_year
ORDER BY corporate_financials.fiscal_year
LIMIT 100;
