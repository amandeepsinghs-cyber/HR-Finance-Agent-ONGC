-- Answer Key SQL: F4
-- Question: How much did royalty, cess and windfall tax reduce realisation per barrel this year?
-- Type: data
-- Semantic audit 2026-10-20: was SUM(statutory_levies) for FY26 LEFT JOINed to 12 monthly price rows (12x fan-out:
-- Semantic audit 2026-10-20: Rs 3,11,988 cr vs actual 25,999 cr) and in crore, not per barrel. Now per-barrel levies
-- Semantic audit 2026-10-20: from price_fx_monthly: 'this year' = FY27 YTD (Apr-Sep 2026, 6 months) with FY26 and FY25
-- Semantic audit 2026-10-20: (SAED year) for context; monthly per-bbl rates averaged within each FY.

SELECT
    fiscal_year,
    COUNT(*) AS months_covered,
    ROUND(AVG(brent_usd_bbl), 2) AS brent_usd_bbl,
    ROUND(AVG(ongc_crude_net_realisation_usd_bbl), 2) AS gross_realisation_usd_bbl,
    ROUND(AVG(royalty_per_barrel_usd), 2) AS royalty_usd_bbl,
    ROUND(AVG(cess_per_barrel_usd), 2) AS oidb_cess_usd_bbl,
    ROUND(AVG(windfall_tax_saed_usd_bbl), 2) AS saed_windfall_usd_bbl,
    ROUND(AVG(royalty_per_barrel_usd + cess_per_barrel_usd + windfall_tax_saed_usd_bbl), 2) AS total_levies_usd_bbl,
    ROUND(AVG(ongc_crude_net_realisation_usd_bbl - royalty_per_barrel_usd - cess_per_barrel_usd - windfall_tax_saed_usd_bbl), 2) AS post_levy_realisation_usd_bbl,
    ROUND(AVG(royalty_per_barrel_usd + cess_per_barrel_usd + windfall_tax_saed_usd_bbl) * 100
          / AVG(ongc_crude_net_realisation_usd_bbl), 1) AS levies_pct_of_realisation,
    ROUND(AVG((royalty_per_barrel_usd + cess_per_barrel_usd + windfall_tax_saed_usd_bbl) * inr_usd_fx_rate), 0) AS total_levies_inr_bbl
FROM price_fx_monthly
WHERE fiscal_year IN ('FY25', 'FY26', 'FY27')
GROUP BY fiscal_year
ORDER BY fiscal_year DESC;
