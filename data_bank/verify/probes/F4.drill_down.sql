-- Probe ID: F4.drill_down
-- Parent ID: F4
-- Answer Type: sql
-- Question: What was the exact dollar-per-barrel impact of OIDB cess (₹10,000/MT equivalent) and royalty on gross crude revenue?
-- Personas: Director (Finance)
-- Tables: price_fx_monthly
-- Drill Dims: price_fx_monthly.month
-- Story IDs: S21
-- Expected Output: table
-- Handcrafted: false

SELECT
    price_fx_monthly.month,
    AVG(price_fx_monthly.cess_per_barrel_usd) AS metric_1,
    AVG(price_fx_monthly.royalty_per_barrel_usd) AS metric_2
FROM price_fx_monthly
WHERE price_fx_monthly.fiscal_year IN ('FY26', '2026')
GROUP BY price_fx_monthly.month
ORDER BY price_fx_monthly.month
LIMIT 100;
