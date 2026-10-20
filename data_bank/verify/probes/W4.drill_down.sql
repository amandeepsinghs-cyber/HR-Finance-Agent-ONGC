-- Probe ID: W4.drill_down
-- Parent ID: W4
-- Answer Type: what_if_sim
-- Question: What was the incremental dollar-per-barrel benefit realized across domestic crude production following the December 2024 SAED removal?
-- Personas: Director (Finance)
-- Tables: price_fx_monthly
-- Drill Dims: price_fx_monthly.month
-- Story IDs: S21
-- Expected Output: table
-- Handcrafted: true

SELECT
    month,
    windfall_tax_saed_usd_bbl
FROM price_fx_monthly
WHERE fiscal_year IN ('FY26', '2026')
ORDER BY month;
