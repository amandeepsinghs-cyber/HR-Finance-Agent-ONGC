-- Answer Key SQL: F1
-- Question: What is the lifting cost ($/bbl) by asset, and which assets are above the company average?
-- Type: data
-- Semantic audit 2026-10-20: was an unweighted AVG of field-level $/BOE ratios with no company average and no
-- Semantic audit 2026-10-20: above/below flag. Now production-weighted (opex / BOE) per asset for FY26 (last full FY),
-- Semantic audit 2026-10-20: field lines only, compared with the production-weighted company average across all fields.

WITH asset AS (
    SELECT
        pnl.asset_wc_id,
        wc.short_name AS asset_name,
        wc.onshore_offshore,
        SUM(pnl.total_production_boe) AS boe,
        SUM(pnl.total_opex_inr_cr) AS opex_cr,
        SUM(pnl.lifting_cost_per_boe_usd * pnl.total_production_boe) AS usd_x_boe
    FROM field_pnl_annual pnl
    JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
    WHERE pnl.fiscal_year = 'FY26'
      AND LOWER(pnl.line_type) = 'field'
      AND pnl.total_production_boe > 0
    GROUP BY pnl.asset_wc_id, wc.short_name, wc.onshore_offshore
),
company AS (
    SELECT ROUND(SUM(usd_x_boe) / SUM(boe), 2) AS company_avg_usd_boe FROM asset
)
SELECT
    a.asset_wc_id,
    a.asset_name,
    a.onshore_offshore,
    ROUND(a.boe / 1e6, 2) AS production_mmboe,
    ROUND(a.opex_cr, 1) AS opex_inr_cr,
    ROUND(a.usd_x_boe / a.boe, 2) AS lifting_cost_usd_boe,
    ROUND(a.opex_cr * 1e7 / a.boe, 0) AS lifting_cost_inr_boe,
    c.company_avg_usd_boe,
    ROUND(a.usd_x_boe / a.boe, 2) > c.company_avg_usd_boe AS above_company_avg
FROM asset a
CROSS JOIN company c
ORDER BY lifting_cost_usd_boe DESC;
