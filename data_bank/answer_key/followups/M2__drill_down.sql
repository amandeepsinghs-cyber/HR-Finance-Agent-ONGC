-- Answer Key Follow-up SQL: M2__drill_down
-- Question: What is the year-to-date capex spend compared to Budget Estimates (BE) across major producing assets?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL used full-year FY26, not year-to-date, and all work centres.
-- Semantic audit 2026-10-20: Now: FY27 YTD (Apr-Sep 2026) actual vs BE for the 15 producing assets, with variance and FY26 production for 'major' context.

WITH prod AS (
    SELECT asset_wc_id, SUM(total_production_boe) / 1e6 AS fy26_mmboe
    FROM production_monthly
    WHERE fiscal_year = 'FY26'
    GROUP BY asset_wc_id
)
SELECT
    wc.short_name AS asset,
    ROUND(prod.fy26_mmboe, 2) AS fy26_mmboe,
    ROUND(SUM(cb.budget_estimate_be_inr_cr), 2) AS ytd_be_inr_cr,
    ROUND(SUM(cb.actual_spend_inr_cr), 2) AS ytd_actual_inr_cr,
    ROUND(SUM(cb.actual_spend_inr_cr) - SUM(cb.budget_estimate_be_inr_cr), 2) AS variance_vs_be_inr_cr,
    ROUND(SUM(cb.actual_spend_inr_cr) * 100.0 / NULLIF(SUM(cb.budget_estimate_be_inr_cr), 0), 1) AS utilisation_vs_be_pct
FROM capex_budget cb
JOIN prod ON prod.asset_wc_id = cb.asset_wc_id
JOIN dim_work_centre wc ON wc.wc_id = cb.asset_wc_id
WHERE cb.fiscal_year = 'FY27'
GROUP BY wc.short_name, prod.fy26_mmboe
ORDER BY fy26_mmboe DESC;
