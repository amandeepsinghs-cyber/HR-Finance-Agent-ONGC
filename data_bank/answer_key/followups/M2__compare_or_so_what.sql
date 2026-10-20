-- Answer Key Follow-up SQL: M2__compare_or_so_what
-- Question: How does the capex expenditure rate in Mumbai High compare with the annual sanctioned budget plan?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL returned FY26 utilisation for every work centre (not Mumbai High, not this year).
-- Semantic audit 2026-10-20: Now: Mumbai High vs company - FY27 YTD actual vs phased BE, annualised run-rate, and FY26 full-year BE/actual as the annual plan reference (FY27 annual BE is not in the data beyond Sep-2026: GAP).

WITH base AS (
    SELECT 'Mumbai High' AS scope, cb.* FROM capex_budget cb WHERE cb.asset_wc_id = 'WC-MUM'
    UNION ALL
    SELECT 'Company total' AS scope, cb.* FROM capex_budget cb
)
SELECT
    scope,
    COUNT(DISTINCT IF(fiscal_year = 'FY27', month, NULL)) AS fy27_months,
    ROUND(SUM(IF(fiscal_year = 'FY27', budget_estimate_be_inr_cr, 0)), 2) AS fy27_ytd_be_inr_cr,
    ROUND(SUM(IF(fiscal_year = 'FY27', actual_spend_inr_cr, 0)), 2) AS fy27_ytd_actual_inr_cr,
    ROUND(SUM(IF(fiscal_year = 'FY27', actual_spend_inr_cr, 0)) * 100.0
          / NULLIF(SUM(IF(fiscal_year = 'FY27', budget_estimate_be_inr_cr, 0)), 0), 1) AS fy27_ytd_utilisation_pct,
    ROUND(SUM(IF(fiscal_year = 'FY27', actual_spend_inr_cr, 0)) * 12.0
          / NULLIF(COUNT(DISTINCT IF(fiscal_year = 'FY27', month, NULL)), 0), 2) AS fy27_annualised_run_rate_inr_cr,
    ROUND(SUM(IF(fiscal_year = 'FY26', budget_estimate_be_inr_cr, 0)), 2) AS fy26_annual_be_inr_cr,
    ROUND(SUM(IF(fiscal_year = 'FY26', actual_spend_inr_cr, 0)), 2) AS fy26_actual_inr_cr,
    ROUND(SUM(IF(fiscal_year = 'FY27', actual_spend_inr_cr, 0)) * 12.0
          / NULLIF(COUNT(DISTINCT IF(fiscal_year = 'FY27', month, NULL)), 0) * 100.0
          / NULLIF(SUM(IF(fiscal_year = 'FY26', budget_estimate_be_inr_cr, 0)), 0), 1) AS run_rate_pct_of_fy26_be
FROM base
WHERE fiscal_year IN ('FY26', 'FY27')
GROUP BY scope
ORDER BY scope DESC;
