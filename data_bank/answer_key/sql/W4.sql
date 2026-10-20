-- Answer Key SQL: W4
-- Question: If the windfall tax is removed, how much does net realisation per barrel improve?
-- Type: what_if
-- Semantic audit 2026-10-20: Old SQL averaged SAED over all 12 months of each FY (incl. months with no levy), diluting the per-barrel uplift (FY23 12.15 vs 16.20 $/bbl when levied; FY25 3.27 vs 4.91).
-- Semantic audit 2026-10-20: Now: per FY, months levied, average SAED $/bbl and Rs/bbl in levied months, last levied rate, FY-average, Brent, realisation and SAED paid (corporate_financials).

SELECT
    p.fiscal_year,
    COUNTIF(p.windfall_tax_saed_usd_bbl > 0) AS months_saed_levied,
    ROUND(AVG(IF(p.windfall_tax_saed_usd_bbl > 0, p.windfall_tax_saed_usd_bbl, NULL)), 2) AS avg_saed_usd_bbl_when_levied,
    ROUND(AVG(IF(p.windfall_tax_saed_usd_bbl > 0, p.windfall_tax_saed_inr_bbl, NULL)), 2) AS avg_saed_inr_bbl_when_levied,
    ARRAY_AGG(IF(p.windfall_tax_saed_usd_bbl > 0, p.windfall_tax_saed_usd_bbl, NULL) IGNORE NULLS ORDER BY p.month DESC LIMIT 1)[SAFE_OFFSET(0)] AS last_levied_saed_usd_bbl,
    ROUND(AVG(p.windfall_tax_saed_usd_bbl), 2) AS fy_avg_saed_usd_bbl,
    ROUND(AVG(p.brent_usd_bbl), 2) AS avg_brent_usd_bbl,
    ROUND(AVG(p.ongc_crude_net_realisation_usd_bbl), 2) AS avg_net_realisation_usd_bbl,
    ROUND(AVG(p.inr_usd_fx_rate), 2) AS avg_fx_rate,
    ANY_VALUE(c.saed_windfall_tax_inr_cr) AS saed_paid_inr_cr
FROM price_fx_monthly p
LEFT JOIN corporate_financials c ON c.fiscal_year = p.fiscal_year
WHERE p.fiscal_year IN ('FY23', 'FY24', 'FY25', 'FY26')
GROUP BY p.fiscal_year
ORDER BY p.fiscal_year;
