-- Answer Key Follow-up SQL: W4__compare_or_so_what
-- Question: How does the post-windfall tax realization compare with historical net realizations during peak oil price cycles?
-- Type: what_if
-- Semantic audit 2026-10-20: Old SQL covered only FY23-FY26, so no earlier price cycle was available for comparison.
-- Semantic audit 2026-10-20: Now: FY17-FY27 YTD average Brent, realisation, realisation % of Brent and SAED, with months covered (FY27 = 6 months, flagged partial) and a Brent rank to identify peak years.

SELECT
    fiscal_year,
    COUNT(*) AS months,
    COUNT(*) < 12 AS is_partial_year,
    ROUND(AVG(brent_usd_bbl), 2) AS avg_brent_usd_bbl,
    ROUND(AVG(ongc_crude_net_realisation_usd_bbl), 2) AS avg_net_realisation_usd_bbl,
    ROUND(AVG(ongc_crude_net_realisation_usd_bbl) * 100.0 / NULLIF(AVG(brent_usd_bbl), 0), 1) AS realisation_pct_of_brent,
    ROUND(AVG(windfall_tax_saed_usd_bbl), 2) AS fy_avg_saed_usd_bbl,
    RANK() OVER (ORDER BY AVG(brent_usd_bbl) DESC) AS brent_rank
FROM price_fx_monthly
GROUP BY fiscal_year
ORDER BY fiscal_year;
