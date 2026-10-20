-- Answer Key Follow-up SQL: F9__drill_down
-- Question: What is our net unhedged foreign currency liability across USD-denominated charter hires, EPC contracts, and equipment imports?
-- Type: data
-- Semantic audit 2026-10-20: summed all currencies and all categories (loans, consulting) in raw USD. Now USD/INR only and
-- Semantic audit 2026-10-20: the three categories asked (rig_charter, subsea_epc, equipment_import): gross, hedged,
-- Semantic audit 2026-10-20: unhedged (USD mn) and unhedged in Rs crore at the latest month's FX (2026-09), plus a total.

WITH fx AS (
    SELECT inr_usd_fx_rate FROM price_fx_monthly WHERE month = '2026-09'
)
SELECT
    COALESCE(h.underlying_contract_category, 'TOTAL (3 categories)') AS contract_category,
    ROUND(SUM(h.gross_exposure_usd) / 1e6, 1) AS gross_exposure_usd_mn,
    ROUND(SUM(h.hedged_amount_usd) / 1e6, 1) AS hedged_usd_mn,
    ROUND(SUM(h.unhedged_exposure_usd) / 1e6, 1) AS unhedged_usd_mn,
    ROUND(SUM(h.hedged_amount_usd) * 100 / SUM(h.gross_exposure_usd), 1) AS hedge_ratio_pct,
    ROUND(SUM(h.unhedged_exposure_usd) * ANY_VALUE(fx.inr_usd_fx_rate) / 1e7, 0) AS unhedged_inr_cr,
    ANY_VALUE(fx.inr_usd_fx_rate) AS fx_rate_used
FROM forex_hedges h
CROSS JOIN fx
WHERE h.fiscal_year = 'FY26'
  AND LOWER(h.hedge_status) = 'active'
  AND h.currency_pair = 'USD/INR'
  AND LOWER(h.underlying_contract_category) IN ('rig_charter', 'subsea_epc', 'equipment_import')
GROUP BY ROLLUP (h.underlying_contract_category)
ORDER BY h.underlying_contract_category IS NULL, unhedged_usd_mn DESC;
