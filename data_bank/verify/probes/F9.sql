-- Probe ID: F9
-- Parent ID: None
-- Answer Type: sql
-- Question: What are the forex exposure and hedging position on dollar-linked contracts?
-- Personas: Director (Finance)
-- Tables: forex_hedges
-- Drill Dims: forex_hedges.currency_pair
-- Story IDs: S25
-- Expected Output: table
-- Handcrafted: false
-- Story Target: 1.85 (total_foreign_currency_debt_usd_bn)
-- Expected Range: 1.67 - 2.04 (tolerance: ±10.0%)

SELECT
    forex_hedges.currency_pair,
    SUM(forex_hedges.gross_exposure_usd) AS metric_1,
    SUM(forex_hedges.hedged_amount_usd) AS metric_2
FROM forex_hedges
WHERE forex_hedges.fiscal_year IN ('FY26', '2026')
GROUP BY forex_hedges.currency_pair
ORDER BY forex_hedges.currency_pair
LIMIT 100;
