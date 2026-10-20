-- Answer Key Follow-up SQL: W4__drill_down
-- Question: What was the incremental dollar-per-barrel benefit realized across domestic crude production following the December 2024 SAED removal?
-- Type: what_if
-- Semantic audit 2026-10-20: Old SQL dumped 12 FY25 monthly rows without a before/after comparison.
-- Semantic audit 2026-10-20: Now: SAED-levied months (Apr-Nov 2024) vs post-removal (Dec 2024-Mar 2025) vs full FY26: average SAED, Brent, realisation, discount to Brent and realisation as % of Brent.

SELECT
    CASE WHEN month BETWEEN '2024-04' AND '2024-11' THEN '1 Apr-Nov 2024 (SAED levied)'
         WHEN month BETWEEN '2024-12' AND '2025-03' THEN '2 Dec 2024-Mar 2025 (SAED removed)'
         ELSE '3 FY26 Apr 2025-Mar 2026 (no SAED)' END AS period,
    COUNT(*) AS months,
    ROUND(AVG(windfall_tax_saed_usd_bbl), 2) AS avg_saed_usd_bbl,
    ROUND(AVG(brent_usd_bbl), 2) AS avg_brent_usd_bbl,
    ROUND(AVG(ongc_crude_net_realisation_usd_bbl), 2) AS avg_net_realisation_usd_bbl,
    ROUND(AVG(brent_usd_bbl - ongc_crude_net_realisation_usd_bbl), 2) AS avg_discount_to_brent_usd_bbl,
    ROUND(AVG(ongc_crude_net_realisation_usd_bbl) * 100.0 / AVG(brent_usd_bbl), 1) AS realisation_pct_of_brent
FROM price_fx_monthly
WHERE fiscal_year IN ('FY25', 'FY26')
GROUP BY period
ORDER BY period;
