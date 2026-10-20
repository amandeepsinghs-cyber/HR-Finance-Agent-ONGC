-- Answer Key Follow-up SQL: C3__compare_or_so_what
-- Question: How does the asset-wise headcount growth compare with the 5-year oil and gas production growth rate across those same assets?
-- Type: data
-- Semantic audit 2026-10-20: old SQL returned only headcount growth (no production at all) for two assets, and
-- that growth was computed by SUMming 12 monthly FY26 snapshots against one FY21 snapshot (+1,182% / +973%).
-- Now: all 15 producing assets (production_monthly.asset_wc_id) plus a company line - headcount growth on
-- period-end snapshots (Mar-21 vs Mar-26) vs FY21->FY26 growth of oil, gas (each in its own unit) and BOE.

WITH hc AS (
    SELECT wc_id,
           SUM(CASE WHEN month = '2021-03' THEN headcount END) AS hc_mar21,
           SUM(CASE WHEN month = '2026-03' THEN headcount END) AS hc_mar26
    FROM headcount_snapshot
    WHERE month IN ('2021-03', '2026-03')
    GROUP BY wc_id
),
prod AS (
    SELECT asset_wc_id AS wc_id,
           SUM(IF(fiscal_year = 'FY21', oil_production_mt + condensate_production_mt, 0)) AS liq21,
           SUM(IF(fiscal_year = 'FY26', oil_production_mt + condensate_production_mt, 0)) AS liq26,
           SUM(IF(fiscal_year = 'FY21', gas_production_mmscm, 0)) AS gas21,
           SUM(IF(fiscal_year = 'FY26', gas_production_mmscm, 0)) AS gas26,
           SUM(IF(fiscal_year = 'FY21', total_production_boe, 0)) AS boe21,
           SUM(IF(fiscal_year = 'FY26', total_production_boe, 0)) AS boe26
    FROM production_monthly
    WHERE fiscal_year IN ('FY21', 'FY26')
    GROUP BY 1
),
j AS (
    SELECT wc.short_name, h.hc_mar21, h.hc_mar26, p.*
    FROM prod p
    JOIN hc h ON h.wc_id = p.wc_id
    JOIN dim_work_centre wc ON wc.wc_id = p.wc_id
),
u AS (
    SELECT short_name, hc_mar21, hc_mar26, liq21, liq26, gas21, gas26, boe21, boe26, 0 AS ord FROM j
    UNION ALL
    SELECT 'All producing assets', SUM(hc_mar21), SUM(hc_mar26), SUM(liq21), SUM(liq26), SUM(gas21), SUM(gas26), SUM(boe21), SUM(boe26), 1 FROM j
)
SELECT
    short_name,
    hc_mar21,
    hc_mar26,
    ROUND((hc_mar26 - hc_mar21) * 100.0 / NULLIF(hc_mar21, 0), 1) AS hc_growth_pct,
    ROUND((liq26 - liq21) * 100.0 / NULLIF(liq21, 0), 1) AS oil_condensate_growth_pct,
    ROUND((gas26 - gas21) * 100.0 / NULLIF(gas21, 0), 1) AS gas_growth_pct,
    ROUND((boe26 - boe21) * 100.0 / NULLIF(boe21, 0), 1) AS boe_growth_pct,
    ROUND(boe21 / 1e6, 2) AS mmboe_fy21,
    ROUND(boe26 / 1e6, 2) AS mmboe_fy26
FROM u
ORDER BY ord, hc_growth_pct DESC;
