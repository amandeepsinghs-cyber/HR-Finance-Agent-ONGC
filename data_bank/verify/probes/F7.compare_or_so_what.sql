-- Probe ID: F7.compare_or_so_what
-- Parent ID: F7
-- Answer Type: sql
-- Question: How does ONGC's overall standalone employee cost ratio compare with global national oil company benchmarks?
-- Personas: Director (Finance)
-- Tables: corporate_financials
-- Drill Dims: corporate_financials.fiscal_year
-- Story IDs: S8
-- Expected Output: number
-- Handcrafted: true

SELECT
    fiscal_year,
    ROUND((employee_cost_total_inr_cr * 100.0) / NULLIF(gross_revenue_inr_cr, 0), 2) AS employee_cost_ratio_pct
FROM corporate_financials
ORDER BY fiscal_year;
