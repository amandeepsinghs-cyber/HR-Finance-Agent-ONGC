-- Answer Key SQL: C11
-- Question: Which assets added headcount but lost production over 5 years?
-- Type: data
-- Semantic audit 2026-10-20: headcount is a stock -> compare period-end snapshots
-- (31-Mar-2021 = month 2021-03 vs 31-Mar-2026 = month 2026-03), never SUM across months.
-- Production is a flow -> full-FY sums (both FY21 and FY26 have 12 months), expressed in BOE
-- (total_production_boe) with oil (MMT) and gas (BCM) shown separately, never added together.
-- Criterion: headcount Mar-26 > Mar-21 AND FY26 BOE < FY21 BOE (flag column).

WITH hc AS (
    SELECT
        wc_id,
        SUM(CASE WHEN month = '2021-03' THEN headcount END) AS hc_mar21,
        SUM(CASE WHEN month = '2026-03' THEN headcount END) AS hc_mar26
    FROM headcount_snapshot
    WHERE month IN ('2021-03', '2026-03')
    GROUP BY wc_id
),
prod AS (
    SELECT
        asset_wc_id AS wc_id,
        SUM(CASE WHEN fiscal_year = 'FY21' THEN total_production_boe END) / 1e6 AS mmboe_fy21,
        SUM(CASE WHEN fiscal_year = 'FY26' THEN total_production_boe END) / 1e6 AS mmboe_fy26,
        SUM(CASE WHEN fiscal_year = 'FY21' THEN oil_production_mt END) / 1e6 AS oil_mmt_fy21,
        SUM(CASE WHEN fiscal_year = 'FY26' THEN oil_production_mt END) / 1e6 AS oil_mmt_fy26,
        SUM(CASE WHEN fiscal_year = 'FY21' THEN gas_production_mmscm END) / 1e3 AS gas_bcm_fy21,
        SUM(CASE WHEN fiscal_year = 'FY26' THEN gas_production_mmscm END) / 1e3 AS gas_bcm_fy26
    FROM production_monthly
    WHERE fiscal_year IN ('FY21', 'FY26')
    GROUP BY asset_wc_id
)
SELECT
    wc.wc_id,
    wc.short_name,
    h.hc_mar21,
    h.hc_mar26,
    h.hc_mar26 - h.hc_mar21 AS hc_change,
    ROUND((h.hc_mar26 - h.hc_mar21) * 100.0 / NULLIF(h.hc_mar21, 0), 2) AS hc_growth_pct,
    ROUND(p.mmboe_fy21, 2) AS mmboe_fy21,
    ROUND(p.mmboe_fy26, 2) AS mmboe_fy26,
    ROUND((p.mmboe_fy26 - p.mmboe_fy21) * 100.0 / NULLIF(p.mmboe_fy21, 0), 2) AS boe_growth_pct,
    ROUND(p.oil_mmt_fy21, 3) AS oil_mmt_fy21,
    ROUND(p.oil_mmt_fy26, 3) AS oil_mmt_fy26,
    ROUND(p.gas_bcm_fy21, 3) AS gas_bcm_fy21,
    ROUND(p.gas_bcm_fy26, 3) AS gas_bcm_fy26,
    (h.hc_mar26 > h.hc_mar21 AND p.mmboe_fy26 < p.mmboe_fy21) AS added_hc_and_lost_production
FROM hc h
JOIN prod p ON h.wc_id = p.wc_id
JOIN dim_work_centre wc ON h.wc_id = wc.wc_id
-- All producing assets are returned with the criterion flag so that an empty qualifying set
-- is still an explicit, checkable answer.
ORDER BY added_hc_and_lost_production DESC, boe_growth_pct ASC;
