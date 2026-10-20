-- Answer Key Follow-up SQL: P17__compare_or_so_what
-- Question: How does the proposed dividend per share (₹13.25) compare with the previous 3-year historical payout trend?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL returned 10 years of payout % without DPS. Now FY23-FY26 (FY26 + previous 3 years) DPS,
-- Semantic audit 2026-10-20: YoY DPS change, dividend and payout % of PAT.
SELECT
    fiscal_year,
    dividend_per_share_inr,
    ROUND(dividend_per_share_inr - LAG(dividend_per_share_inr) OVER (ORDER BY fiscal_year), 2) AS dps_change_inr,
    ROUND(100 * (dividend_per_share_inr / LAG(dividend_per_share_inr) OVER (ORDER BY fiscal_year) - 1), 1) AS dps_change_pct,
    total_dividend_payout_inr_cr AS dividend_cr,
    pat_inr_cr,
    ROUND(100 * total_dividend_payout_inr_cr / NULLIF(pat_inr_cr, 0), 1) AS payout_pct_of_pat
FROM corporate_financials
WHERE fiscal_year BETWEEN 'FY22' AND 'FY26'
QUALIFY fiscal_year >= 'FY23'
ORDER BY fiscal_year;
