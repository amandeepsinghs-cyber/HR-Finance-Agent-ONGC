-- Answer Key Follow-up SQL: W4__why
-- Question: Why did the Special Additional Excise Duty (SAED) previously compress ONGC net realizations below international benchmarks?
-- Type: what_if
-- Semantic audit 2026-10-20: Old SQL returned SAED crore, revenue and EBITDA only - no benchmark gap.
-- Semantic audit 2026-10-20: Now: FY22-FY26 average Brent vs realisation (gap to benchmark), SAED $/bbl, SAED paid and SAED as % of gross revenue.

WITH px AS (
    SELECT fiscal_year,
           AVG(brent_usd_bbl) AS brent,
           AVG(ongc_crude_net_realisation_usd_bbl) AS realisation,
           AVG(windfall_tax_saed_usd_bbl) AS saed
    FROM price_fx_monthly
    WHERE fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
    GROUP BY fiscal_year
)
SELECT
    px.fiscal_year,
    ROUND(px.brent, 2) AS avg_brent_usd_bbl,
    ROUND(px.realisation, 2) AS avg_net_realisation_usd_bbl,
    ROUND(px.brent - px.realisation, 2) AS gap_to_brent_usd_bbl,
    ROUND(px.saed, 2) AS fy_avg_saed_usd_bbl,
    c.saed_windfall_tax_inr_cr,
    c.gross_revenue_inr_cr,
    ROUND(c.saed_windfall_tax_inr_cr * 100.0 / NULLIF(c.gross_revenue_inr_cr, 0), 2) AS saed_pct_of_revenue
FROM px
JOIN corporate_financials c ON c.fiscal_year = px.fiscal_year
ORDER BY px.fiscal_year;
