-- Probe ID: M4.drill_down
-- Parent ID: M4
-- Answer Type: sql
-- Question: What is the company-wide crude oil and gas production volume published in the public quarterly report?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: production_monthly
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: table
-- Handcrafted: false

SELECT
    SUM(production_monthly.oil_production_mt) AS metric_1,
    SUM(production_monthly.gas_production_mmscm) AS metric_2
FROM production_monthly
WHERE production_monthly.fiscal_year IN ('FY26', '2026')
ORDER BY 1
LIMIT 100;
