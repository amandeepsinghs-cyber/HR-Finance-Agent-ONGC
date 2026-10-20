-- Answer Key Follow-up SQL: P17__why
-- Question: What capital expenditure commitments (₹35,878 cr capex) and debt obligations constrain increasing the dividend payout ratio?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL showed revenue/capex/dividend for FY24-FY26 without the funding arithmetic. Now FY22-FY26
-- Semantic audit 2026-10-20: internal accruals (PAT + DD&A) less dividend vs capex = funding surplus/gap. GAP: no borrowings /
-- Semantic audit 2026-10-20: debt-service data exists in silver, so "debt obligations" cannot be quantified.
SELECT
    fiscal_year,
    pat_inr_cr,
    dda_inr_cr,
    total_dividend_payout_inr_cr AS dividend_cr,
    total_capex_spent_inr_cr AS capex_cr,
    ROUND(pat_inr_cr + dda_inr_cr - total_dividend_payout_inr_cr, 0) AS accruals_after_dividend_cr,
    ROUND(pat_inr_cr + dda_inr_cr - total_dividend_payout_inr_cr - total_capex_spent_inr_cr, 0) AS funding_surplus_cr,
    ROUND(100 * total_capex_spent_inr_cr / (pat_inr_cr + dda_inr_cr), 1) AS capex_pct_of_accruals,
    dividend_payout_ratio_pct
FROM `ongc-hr-finance-agent.hrfin_silver.corporate_financials`
WHERE fiscal_year BETWEEN 'FY22' AND 'FY26'
ORDER BY fiscal_year DESC;
