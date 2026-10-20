-- Probe ID: F9.drill_down
-- Parent ID: F9
-- Answer Type: sql
-- Question: What is our net unhedged foreign currency liability across USD-denominated charter hires, EPC contracts, and equipment imports?
-- Personas: Director (Finance)
-- Tables: forex_hedges
-- Drill Dims: forex_hedges.underlying_contract_category
-- Story IDs: S25
-- Expected Output: chart
-- Handcrafted: false

SELECT
    forex_hedges.underlying_contract_category,
    SUM(forex_hedges.unhedged_exposure_usd) AS metric_1
FROM forex_hedges
WHERE forex_hedges.fiscal_year IN ('FY26', '2026')
GROUP BY forex_hedges.underlying_contract_category
ORDER BY forex_hedges.underlying_contract_category
LIMIT 100;
