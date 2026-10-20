-- Probe ID: X4.drill_down
-- Parent ID: X4
-- Answer Type: sql
-- Question: What is the discount rate and salary escalation assumption used by the actuary for each scheme?
-- Personas: Director (Finance)
-- Tables: benefit_liabilities
-- Drill Dims: benefit_liabilities.scheme_name
-- Story IDs: S32
-- Expected Output: table
-- Handcrafted: true

SELECT
    scheme_name,
    discount_rate_pct,
    salary_escalation_rate_pct,
    medical_inflation_rate_pct
FROM benefit_liabilities
WHERE fiscal_year IN ('FY26', '2026')
ORDER BY scheme_name;
