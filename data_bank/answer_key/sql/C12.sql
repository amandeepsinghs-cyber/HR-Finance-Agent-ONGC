-- Answer Key SQL: C12
-- Question: What is the manpower cost per barrel of oil equivalent (BOE), by asset?
-- Type: data
-- Semantic audit 2026-10-20: old SQL computed manpower cost as a % of revenue (not per BOE), at field grain
-- labelled with the asset name (59 rows incl. plant/corporate P&L lines, the same asset repeated). Now: FY26,
-- field P&L lines aggregated to producing asset - allocated manpower cost x 1e7 / total BOE (ratio of sums,
-- MET-FIN-009 pattern) in INR and in USD at the FY26 average INR/USD from dim_price_fx, with headcount and
-- BOE per employee; plus a company line over all producing assets.

WITH a AS (
    SELECT pnl.asset_wc_id,
           SUM(pnl.allocated_manpower_cost_inr_cr) AS manpower_cr,
           SUM(pnl.total_production_boe) AS boe,
           SUM(pnl.regular_employee_headcount) AS regular_headcount
    FROM field_pnl_annual pnl
    WHERE pnl.fiscal_year = 'FY26' AND LOWER(pnl.line_type) = 'field'
    GROUP BY pnl.asset_wc_id
),
fx AS (SELECT AVG(inr_usd_fx_rate) AS fx FROM dim_price_fx WHERE fiscal_year = 'FY26'),
u AS (
    SELECT wc.short_name AS asset, wc.onshore_offshore, 0 AS ord, a.manpower_cr, a.boe, a.regular_headcount
    FROM a JOIN dim_work_centre wc ON wc.wc_id = a.asset_wc_id
    UNION ALL
    SELECT 'All producing assets', 'all', 1, SUM(manpower_cr), SUM(boe), SUM(regular_headcount) FROM a
)
SELECT
    u.asset,
    u.onshore_offshore,
    ROUND(u.manpower_cr, 1) AS manpower_cost_inr_cr,
    ROUND(u.boe / 1e6, 2) AS mmboe_fy26,
    ROUND(u.manpower_cr * 1e7 / NULLIF(u.boe, 0), 0) AS manpower_cost_inr_per_boe,
    ROUND(u.manpower_cr * 1e7 / NULLIF(u.boe, 0) / fx.fx, 2) AS manpower_cost_usd_per_boe,
    u.regular_headcount,
    ROUND(u.boe / NULLIF(u.regular_headcount, 0), 0) AS boe_per_employee
FROM u CROSS JOIN fx
ORDER BY u.ord, manpower_cost_usd_per_boe DESC;
