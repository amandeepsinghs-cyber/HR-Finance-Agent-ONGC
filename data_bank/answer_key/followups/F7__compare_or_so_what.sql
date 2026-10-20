-- Answer Key Follow-up SQL: F7__compare_or_so_what
-- Question: How does ONGC's overall standalone employee cost ratio compare with global national oil company benchmarks?
-- Type: data

SELECT
    fiscal_year,
    ROUND((employee_cost_total_inr_cr * 100.0) / NULLIF(gross_revenue_inr_cr, 0), 2) AS employee_cost_ratio_pct
FROM corporate_financials
ORDER BY fiscal_year;
