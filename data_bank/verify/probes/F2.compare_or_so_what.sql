-- Probe ID: F2.compare_or_so_what
-- Parent ID: F2
-- Answer Type: sql
-- Question: How does total capital expenditure across all assets compare between Budget Estimates (BE) and Revised Estimates (RE) over 5 years?
-- Personas: Director (Finance)
-- Tables: capex_budget
-- Drill Dims: capex_budget.fiscal_year
-- Story IDs: S9
-- Expected Output: table
-- Handcrafted: true

SELECT
    fiscal_year,
    ROUND(SUM(budget_estimate_be_inr_cr), 2) AS total_be_cr,
    ROUND(SUM(revised_estimate_re_inr_cr), 2) AS total_re_cr,
    ROUND(SUM(actual_spend_inr_cr), 2) AS total_actual_spend_cr
FROM capex_budget
WHERE fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
GROUP BY fiscal_year
ORDER BY fiscal_year;
