-- Answer Key SQL: D4
-- Question: Which fields are loss-making, and what is the capex plan for next year?
-- Type: refusal

SELECT
    fiscal_year,
    gross_revenue_inr_cr,
    total_capex_spent_inr_cr,
    pat_inr_cr
FROM `ongc-hr-finance-agent.hrfin_gold.mart_corporate_performance`
WHERE fiscal_year IS NOT NULL
GROUP BY fiscal_year, gross_revenue_inr_cr, total_capex_spent_inr_cr, pat_inr_cr
ORDER BY fiscal_year DESC
LIMIT 5;
