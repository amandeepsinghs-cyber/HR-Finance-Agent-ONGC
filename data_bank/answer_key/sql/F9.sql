-- Answer Key SQL: F9
-- Question: What are the forex exposure and hedging position on dollar-linked contracts?
-- Type: data
-- Semantic audit 2026-10-20: unlabelled sums in raw USD by currency only. Now FY26 active book by currency pair in USD
-- Semantic audit 2026-10-20: million: gross exposure, hedged via derivatives vs natural hedge (crude-sales designated),
-- Semantic audit 2026-10-20: unhedged, hedge ratio and MTM (Rs cr). Non-USD exposures are stated in USD equivalent.

SELECT
    COALESCE(fh.currency_pair, 'ALL CURRENCIES') AS currency_pair,
    COUNT(*) AS positions,
    ROUND(SUM(gross_exposure_usd) / 1e6, 1) AS gross_exposure_usd_mn,
    ROUND(SUM(IF(LOWER(instrument_type) LIKE 'natural_hedge%', hedged_amount_usd, 0)) / 1e6, 1) AS natural_hedge_usd_mn,
    ROUND(SUM(IF(LOWER(instrument_type) NOT LIKE 'natural_hedge%', hedged_amount_usd, 0)) / 1e6, 1) AS derivative_hedged_usd_mn,
    ROUND(SUM(unhedged_exposure_usd) / 1e6, 1) AS unhedged_usd_mn,
    ROUND(SUM(hedged_amount_usd) * 100 / SUM(gross_exposure_usd), 1) AS hedge_ratio_pct,
    ROUND(SUM(mtm_gain_loss_inr_cr), 1) AS mtm_gain_loss_inr_cr
FROM forex_hedges fh
WHERE fiscal_year = 'FY26' AND LOWER(hedge_status) = 'active'
GROUP BY ROLLUP (fh.currency_pair)
ORDER BY GROUPING(fh.currency_pair), gross_exposure_usd_mn DESC;
