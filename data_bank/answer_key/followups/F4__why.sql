-- Answer Key Follow-up SQL: F4__why
-- Question: What were the structural statutory reasons for windfall tax (SAED) variations prior to its discontinuation in December 2024?
-- Type: data
-- Semantic audit 2026-10-20: cited G-01 Part 1 (a DPE pay-revision OM) - irrelevant to SAED. The document corpus has no
-- Semantic audit 2026-10-20: SAED notification (GAP), so the answer is now evidenced from data: SAED $/bbl vs Brent per FY
-- Semantic audit 2026-10-20: (price_fx_monthly, FY23-FY26) and SAED booked in corporate_financials (one row per FY, joined
-- Semantic audit 2026-10-20: after monthly aggregation, so no fan-out).

WITH px AS (
    SELECT
        fiscal_year,
        COUNT(*) AS months,
        COUNTIF(windfall_tax_saed_usd_bbl > 0) AS months_saed_levied,
        ROUND(AVG(brent_usd_bbl), 1) AS avg_brent_usd_bbl,
        ROUND(MAX(brent_usd_bbl), 1) AS max_brent_usd_bbl,
        ROUND(AVG(windfall_tax_saed_usd_bbl), 2) AS avg_saed_usd_bbl,
        ROUND(MAX(windfall_tax_saed_usd_bbl), 2) AS max_saed_usd_bbl,
        ROUND(AVG(IF(windfall_tax_saed_usd_bbl > 0, windfall_tax_saed_usd_bbl * 100 / brent_usd_bbl, NULL)), 1) AS saed_pct_of_brent_when_levied,
        MAX(IF(windfall_tax_saed_usd_bbl > 0, month, NULL)) AS last_month_levied
    FROM price_fx_monthly
    WHERE fiscal_year IN ('FY23', 'FY24', 'FY25', 'FY26')
    GROUP BY fiscal_year
)
SELECT
    px.*,
    cf.saed_windfall_tax_inr_cr AS saed_booked_inr_cr,
    ROUND(cf.saed_windfall_tax_inr_cr * 100 / cf.statutory_levies_total_inr_cr, 1) AS saed_share_of_levies_pct
FROM px
JOIN corporate_financials cf USING (fiscal_year)
ORDER BY px.fiscal_year;
