-- Answer Key Follow-up SQL: P17__drill_down
-- Question: What is the minimum dividend requirement under DIPAM guidelines (5% of net worth or 30% of PAT) for FY26?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL listed DPS/payout for all years without computing the DIPAM minimum. Now FY22-FY26:
-- Semantic audit 2026-10-20: 30%-of-PAT floor vs actual dividend. GAP: net worth is not in corporate_financials, so the
-- Semantic audit 2026-10-20: 5%-of-net-worth leg (higher-of test) cannot be computed; the 30%-of-PAT leg is a lower bound.
SELECT
    fiscal_year,
    pat_inr_cr,
    ROUND(0.30 * pat_inr_cr, 0) AS dipam_floor_30pct_pat_cr,
    total_dividend_payout_inr_cr AS actual_dividend_cr,
    ROUND(total_dividend_payout_inr_cr - 0.30 * pat_inr_cr, 0) AS above_floor_cr,
    ROUND(100 * total_dividend_payout_inr_cr / pat_inr_cr, 1) AS payout_pct_of_pat,
    CAST(NULL AS FLOAT64) AS net_worth_5pct_leg_cr
FROM corporate_financials
WHERE fiscal_year BETWEEN 'FY22' AND 'FY26'
ORDER BY fiscal_year DESC;
