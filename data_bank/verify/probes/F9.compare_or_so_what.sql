-- Probe ID: F9.compare_or_so_what
-- Parent ID: F9
-- Answer Type: sql
-- Question: How does the natural hedge from dollar-denominated crude sales compare against foreign exchange rate volatility on opex and capex?
-- Personas: Director (Finance)
-- Tables: forex_hedges, corporate_financials
-- Drill Dims: 
-- Story IDs: S25
-- Expected Output: table
-- Handcrafted: false

SELECT
    SUM(forex_hedges.gross_exposure_usd) AS metric_1
FROM forex_hedges
LEFT JOIN corporate_financials ON corporate_financials.fiscal_year = forex_hedges.fiscal_year
WHERE forex_hedges.fiscal_year IN ('FY26', '2026')
ORDER BY 1
LIMIT 100;
