-- Answer Key Follow-up SQL: F4__drill_down
-- Question: What was the exact dollar-per-barrel impact of OIDB cess (₹10,000/MT equivalent) and royalty on gross crude revenue?
-- Type: data
-- Semantic audit 2026-10-20: was FY26 monthly cess/royalty (parent is FY27 YTD), unnamed metric columns, no link to the
-- Semantic audit 2026-10-20: Rs 10,000/MT reference or to gross realisation. Now FY27 YTD by month: cess and royalty
-- Semantic audit 2026-10-20: $/bbl, each as % of gross realisation, and the Rs 10,000/MT cess converted to $/bbl at the
-- Semantic audit 2026-10-20: month's FX using 7.33 bbl per tonne (glossary BOE factor).

SELECT
    month,
    ROUND(ongc_crude_net_realisation_usd_bbl, 2) AS gross_realisation_usd_bbl,
    ROUND(cess_per_barrel_usd, 2) AS oidb_cess_usd_bbl,
    ROUND(cess_per_barrel_usd * 100 / ongc_crude_net_realisation_usd_bbl, 1) AS cess_pct_of_realisation,
    ROUND(10000 / 7.33 / inr_usd_fx_rate, 2) AS cess_at_rs10000_per_mt_usd_bbl,
    ROUND(royalty_per_barrel_usd, 2) AS royalty_usd_bbl,
    ROUND(royalty_per_barrel_usd * 100 / ongc_crude_net_realisation_usd_bbl, 1) AS royalty_pct_of_realisation,
    ROUND(cess_per_barrel_usd + royalty_per_barrel_usd, 2) AS cess_plus_royalty_usd_bbl,
    inr_usd_fx_rate
FROM price_fx_monthly
WHERE fiscal_year = 'FY27'
ORDER BY month;
