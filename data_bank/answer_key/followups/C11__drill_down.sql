-- Answer Key Follow-up SQL: C11__drill_down
-- Question: What is the specific 5-year headcount change and crude/gas output variance for Mehsana, Assam, and Rajahmundry assets?
-- Type: data
-- Semantic audit 2026-10-20: old SQL SUMmed headcount_snapshot over every month of FY21 (1 month) and FY26 (12
-- months) - e.g. Assam 2,480 -> 22,439 - and returned no production at all. Now: period-end headcount
-- 31-Mar-2021 vs 31-Mar-2026 (months '2021-03' / '2026-03') and full-FY production FY21 vs FY26 (12 months
-- each): crude (oil + condensate, MMT) and gas (BCM) kept in their own units, never added together.

WITH hc AS (
    SELECT wc_id,
           SUM(CASE WHEN month = '2021-03' THEN headcount END) AS hc_mar21,
           SUM(CASE WHEN month = '2026-03' THEN headcount END) AS hc_mar26
    FROM headcount_snapshot
    WHERE month IN ('2021-03', '2026-03') AND wc_id IN ('WC-MEH', 'WC-ASM', 'WC-RAJ')
    GROUP BY wc_id
),
prod AS (
    SELECT asset_wc_id AS wc_id,
           SUM(IF(fiscal_year = 'FY21', oil_production_mt + condensate_production_mt, 0)) / 1e6 AS crude_mmt_fy21,
           SUM(IF(fiscal_year = 'FY26', oil_production_mt + condensate_production_mt, 0)) / 1e6 AS crude_mmt_fy26,
           SUM(IF(fiscal_year = 'FY21', gas_production_mmscm, 0)) / 1e3 AS gas_bcm_fy21,
           SUM(IF(fiscal_year = 'FY26', gas_production_mmscm, 0)) / 1e3 AS gas_bcm_fy26
    FROM production_monthly
    WHERE fiscal_year IN ('FY21', 'FY26') AND asset_wc_id IN ('WC-MEH', 'WC-ASM', 'WC-RAJ')
    GROUP BY 1
)
SELECT
    wc.short_name,
    h.hc_mar21,
    h.hc_mar26,
    h.hc_mar26 - h.hc_mar21 AS hc_change,
    ROUND((h.hc_mar26 - h.hc_mar21) * 100.0 / NULLIF(h.hc_mar21, 0), 1) AS hc_change_pct,
    ROUND(p.crude_mmt_fy21, 3) AS crude_mmt_fy21,
    ROUND(p.crude_mmt_fy26, 3) AS crude_mmt_fy26,
    ROUND((p.crude_mmt_fy26 - p.crude_mmt_fy21) * 100.0 / NULLIF(p.crude_mmt_fy21, 0), 1) AS crude_variance_pct,
    ROUND(p.gas_bcm_fy21, 3) AS gas_bcm_fy21,
    ROUND(p.gas_bcm_fy26, 3) AS gas_bcm_fy26,
    ROUND((p.gas_bcm_fy26 - p.gas_bcm_fy21) * 100.0 / NULLIF(p.gas_bcm_fy21, 0), 1) AS gas_variance_pct
FROM hc h
JOIN prod p ON p.wc_id = h.wc_id
JOIN dim_work_centre wc ON wc.wc_id = h.wc_id
ORDER BY hc_change_pct;
