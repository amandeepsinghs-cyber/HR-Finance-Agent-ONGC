-- Answer Key SQL: P17
-- Question: Does our dividend policy allow a higher payout this year, given the capex plan?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL returned only FY26 PAT/dividend/DPS and ignored the capex plan the question hinges on.
-- Semantic audit 2026-10-20: Now FY26 (last full FY) payout vs DIPAM floor (30% of PAT; 5%-of-net-worth leg not computable: no
-- Semantic audit 2026-10-20: net worth in data), internal accruals after dividend (PAT + DD&A - dividend) vs capex, and the
-- Semantic audit 2026-10-20: max extra DPS = surplus / implied share count (dividend / DPS); current-year capex run-rate: FY27 Apr-Sep actual vs FY26 Apr-Sep actual (equal 6-month coverage, capex_budget).
WITH h1 AS (
    SELECT
        SUM(IF(fiscal_year = 'FY27', actual_spend_inr_cr, 0)) AS fy27_h1_capex_cr,
        SUM(IF(fiscal_year = 'FY26' AND month BETWEEN '2025-04' AND '2025-09', actual_spend_inr_cr, 0)) AS fy26_h1_capex_cr,
        SUM(IF(fiscal_year = 'FY27', budget_estimate_be_inr_cr, 0)) AS fy27_h1_capex_be_cr
    FROM capex_budget
    WHERE fiscal_year IN ('FY26', 'FY27')
)
SELECT
    f.fiscal_year,
    f.pat_inr_cr,
    f.total_dividend_payout_inr_cr AS dividend_cr,
    f.dividend_per_share_inr,
    ROUND(100 * f.total_dividend_payout_inr_cr / f.pat_inr_cr, 1) AS payout_pct_of_pat,
    ROUND(0.30 * f.pat_inr_cr, 0) AS dipam_floor_30pct_pat_cr,
    ROUND(f.total_dividend_payout_inr_cr - 0.30 * f.pat_inr_cr, 0) AS paid_above_floor_cr,
    f.dda_inr_cr,
    f.total_capex_spent_inr_cr AS capex_cr,
    ROUND(f.pat_inr_cr + f.dda_inr_cr - f.total_dividend_payout_inr_cr, 0) AS accruals_after_dividend_cr,
    ROUND(f.pat_inr_cr + f.dda_inr_cr - f.total_dividend_payout_inr_cr - f.total_capex_spent_inr_cr, 0) AS surplus_after_capex_cr,
    ROUND((f.pat_inr_cr + f.dda_inr_cr - f.total_dividend_payout_inr_cr - f.total_capex_spent_inr_cr)
          / (f.total_dividend_payout_inr_cr / f.dividend_per_share_inr), 2) AS max_extra_dps_from_surplus_inr,
    ROUND(h1.fy26_h1_capex_cr, 0) AS fy26_apr_sep_capex_cr,
    ROUND(h1.fy27_h1_capex_cr, 0) AS fy27_apr_sep_capex_cr,
    ROUND(h1.fy27_h1_capex_be_cr, 0) AS fy27_apr_sep_capex_be_cr,
    ROUND(100 * (h1.fy27_h1_capex_cr - h1.fy26_h1_capex_cr) / h1.fy26_h1_capex_cr, 1) AS capex_h1_change_pct
FROM corporate_financials f, h1
WHERE f.fiscal_year = 'FY26';
