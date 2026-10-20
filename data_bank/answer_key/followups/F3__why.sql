-- Answer Key Follow-up SQL: F3__why
-- Question: What combination of oil price fluctuations, cess rates, and workover costs drove margin compression in mature onshore fields?
-- Type: data
-- Semantic audit 2026-10-20: was FY26 average water cut by field (none of price, cess or workover). Now, for mature
-- Semantic audit 2026-10-20: onshore fields (dim_field maturity/onshore), FY22-FY26 by year: Brent and ONGC net
-- Semantic audit 2026-10-20: realisation (price_fx_monthly, aggregated per FY before joining), revenue, cess, royalty,
-- Semantic audit 2026-10-20: SAED, levies % of revenue, workover cost, opex per BOE and EBITDA margin.

WITH px AS (
    SELECT fiscal_year,
           AVG(brent_usd_bbl) AS brent,
           AVG(ongc_crude_net_realisation_usd_bbl) AS net_realisation
    FROM price_fx_monthly
    GROUP BY fiscal_year
),
m AS (
    SELECT
        pnl.fiscal_year,
        SUM(pnl.gross_revenue_inr_cr) AS rev,
        SUM(pnl.statutory_cess_inr_cr) AS cess,
        SUM(pnl.statutory_royalty_inr_cr) AS royalty,
        SUM(pnl.statutory_windfall_tax_saed_inr_cr) AS saed,
        SUM(pnl.workover_repairs_cost_inr_cr) AS workover,
        SUM(pnl.total_opex_inr_cr) AS opex,
        SUM(pnl.ebitda_inr_cr) AS ebitda,
        SUM(pnl.total_production_boe) AS boe
    FROM field_pnl_annual pnl
    JOIN dim_field f ON f.field_id = pnl.field_id
    WHERE LOWER(f.onshore_offshore) = 'onshore' AND LOWER(f.maturity) = 'mature'
      AND pnl.fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
      AND LOWER(pnl.line_type) = 'field'
    GROUP BY pnl.fiscal_year
)
SELECT
    m.fiscal_year,
    ROUND(px.brent, 1) AS brent_usd_bbl,
    ROUND(px.net_realisation, 1) AS net_realisation_usd_bbl,
    ROUND(m.rev, 0) AS revenue_cr,
    ROUND(m.cess, 0) AS cess_cr,
    ROUND(m.royalty, 0) AS royalty_cr,
    ROUND(m.saed, 0) AS saed_windfall_cr,
    ROUND((m.cess + m.royalty + m.saed) * 100 / m.rev, 1) AS levies_pct_revenue,
    ROUND(m.workover, 0) AS workover_cr,
    ROUND(m.opex * 1e7 / m.boe, 0) AS opex_inr_per_boe,
    ROUND(m.boe / 1e6, 1) AS production_mmboe,
    ROUND(m.ebitda * 100 / m.rev, 1) AS ebitda_margin_pct
FROM m
JOIN px USING (fiscal_year)
ORDER BY m.fiscal_year;
