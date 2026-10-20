-- Probe ID: D4.drill_down
-- Parent ID: D4
-- Answer Type: sql
-- Question: What is the company-wide crude oil and natural gas production volume published in the latest annual report?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: production_monthly
-- Drill Dims: production_monthly.fiscal_year
-- Story IDs: 
-- Expected Output: table
-- Handcrafted: false

SELECT
    production_monthly.fiscal_year,
    SUM(production_monthly.oil_production_mt) AS metric_1,
    SUM(production_monthly.gas_production_mmscm) AS metric_2
FROM production_monthly
WHERE production_monthly.fiscal_year IN ('FY26', '2026')
GROUP BY production_monthly.fiscal_year
ORDER BY production_monthly.fiscal_year
LIMIT 100;
