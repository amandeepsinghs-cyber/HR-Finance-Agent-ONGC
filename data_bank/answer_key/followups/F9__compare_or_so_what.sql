-- Answer Key Follow-up SQL: F9__compare_or_so_what
-- Question: How does the natural hedge from dollar-denominated crude sales compare against foreign exchange rate volatility on opex and capex?
-- Type: data
-- Semantic audit 2026-10-20: returned only total gross exposure (raw USD). Now FY26: crude (oil) revenue in USD at the
-- Semantic audit 2026-10-20: average FX, exposure designated against the natural hedge, derivative cover, unhedged
-- Semantic audit 2026-10-20: exposure, FY26 INR/USD range and monthly volatility, and the Rs impact of the FY26 FX range on
-- Semantic audit 2026-10-20: the unhedged book. GAP: no USD split of opex/capex exists, so exposure uses the hedge book.

WITH fx AS (
    SELECT AVG(inr_usd_fx_rate) AS avg_fx, MIN(inr_usd_fx_rate) AS min_fx, MAX(inr_usd_fx_rate) AS max_fx,
           STDDEV_SAMP(inr_usd_fx_rate) AS sd_fx
    FROM price_fx_monthly WHERE fiscal_year = 'FY26'
),
crude AS (
    SELECT SUM(oil_revenue_inr_cr) AS oil_rev_cr
    FROM field_pnl_annual WHERE fiscal_year = 'FY26' AND LOWER(line_type) = 'field'
),
book AS (
    SELECT
        SUM(gross_exposure_usd) AS gross,
        SUM(IF(LOWER(instrument_type) LIKE 'natural_hedge%', hedged_amount_usd, 0)) AS nat_hedge,
        SUM(IF(LOWER(instrument_type) NOT LIKE 'natural_hedge%', hedged_amount_usd, 0)) AS deriv,
        SUM(unhedged_exposure_usd) AS unhedged
    FROM forex_hedges WHERE fiscal_year = 'FY26' AND LOWER(hedge_status) = 'active'
)
SELECT
    ROUND(crude.oil_rev_cr, 0) AS crude_revenue_fy26_inr_cr,
    ROUND(crude.oil_rev_cr * 1e7 / fx.avg_fx / 1e6, 0) AS crude_revenue_fy26_usd_mn,
    ROUND(book.gross / 1e6, 0) AS fx_exposure_usd_mn,
    ROUND(book.nat_hedge / 1e6, 0) AS natural_hedge_designated_usd_mn,
    ROUND(book.deriv / 1e6, 0) AS derivative_hedged_usd_mn,
    ROUND(book.unhedged / 1e6, 0) AS unhedged_usd_mn,
    ROUND(crude.oil_rev_cr * 1e7 / fx.avg_fx / book.gross, 1) AS crude_usd_cover_of_exposure_x,
    ROUND(fx.avg_fx, 2) AS fx_avg_fy26,
    ROUND(fx.min_fx, 2) AS fx_min_fy26,
    ROUND(fx.max_fx, 2) AS fx_max_fy26,
    ROUND(fx.sd_fx * 100 / fx.avg_fx, 2) AS fx_volatility_pct,
    ROUND(book.unhedged * (fx.max_fx - fx.min_fx) / 1e7, 0) AS unhedged_impact_of_fy26_fx_range_inr_cr,
    ROUND(crude.oil_rev_cr * 1e7 / fx.avg_fx * (fx.max_fx - fx.min_fx) / 1e7, 0) AS crude_revenue_swing_of_fy26_fx_range_inr_cr
FROM crude CROSS JOIN fx CROSS JOIN book;
