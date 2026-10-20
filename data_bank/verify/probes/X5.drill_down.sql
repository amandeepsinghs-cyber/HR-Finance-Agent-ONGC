-- Probe ID: X5.drill_down
-- Parent ID: X5
-- Answer Type: sql
-- Question: What was the dividend received by ONGC from each group company in FY26?
-- Personas: Director (Finance)
-- Tables: subsidiary_financials
-- Drill Dims: subsidiary_financials.entity_code
-- Story IDs: S33
-- Expected Output: table
-- Handcrafted: true

SELECT
    entity_code,
    entity_name,
    dividend_received_by_ongc_inr_cr
FROM subsidiary_financials
WHERE fiscal_year IN ('FY26', '2026')
ORDER BY dividend_received_by_ongc_inr_cr DESC;
