-- Answer Key Follow-up SQL: C3__why
-- Question: What operational developments (e.g. KG-DWN-98/2 deepwater ramp-up vs mature field natural decline) drove this headcount shift?
-- Type: data
-- Semantic audit 2026-10-20: old SQL showed only oil/gas for two assets with no link to headcount. Now, for the
-- four drill-down assets: March-21 vs March-26 headcount (period-end snapshots), full-FY production in BOE
-- (FY21 and FY26 both have 12 months; oil MMT and gas BCM shown separately, never added) and the field
-- maturity mix from dim_field. (active_producing_wells was tested but is static FY21=FY26 per asset - see
-- data_defects_C.yaml - so it is not used as evidence.)

WITH hc AS (
    SELECT wc_id,
           SUM(CASE WHEN month = '2021-03' THEN headcount END) AS hc_mar21,
           SUM(CASE WHEN month = '2026-03' THEN headcount END) AS hc_mar26
    FROM headcount_snapshot
    WHERE month IN ('2021-03', '2026-03') AND wc_id IN ('WC-EAS', 'WC-RAJ', 'WC-MEH', 'WC-CAM')
    GROUP BY wc_id
),
pm AS (
    SELECT asset_wc_id AS wc_id, fiscal_year, month,
           SUM(total_production_boe) AS boe, SUM(oil_production_mt) AS oil_mt, SUM(gas_production_mmscm) AS gas_mmscm
    FROM production_monthly
    WHERE fiscal_year IN ('FY21', 'FY26') AND asset_wc_id IN ('WC-EAS', 'WC-RAJ', 'WC-MEH', 'WC-CAM')
    GROUP BY 1, 2, 3
),
prod AS (
    SELECT wc_id,
           SUM(IF(fiscal_year = 'FY21', boe, 0)) / 1e6 AS mmboe_fy21,
           SUM(IF(fiscal_year = 'FY26', boe, 0)) / 1e6 AS mmboe_fy26,
           SUM(IF(fiscal_year = 'FY21', oil_mt, 0)) / 1e6 AS oil_mmt_fy21,
           SUM(IF(fiscal_year = 'FY26', oil_mt, 0)) / 1e6 AS oil_mmt_fy26,
           SUM(IF(fiscal_year = 'FY21', gas_mmscm, 0)) / 1e3 AS gas_bcm_fy21,
           SUM(IF(fiscal_year = 'FY26', gas_mmscm, 0)) / 1e3 AS gas_bcm_fy26
    FROM pm
    GROUP BY wc_id
),
mat AS (
    SELECT asset_wc_id AS wc_id, STRING_AGG(DISTINCT maturity, '/' ORDER BY maturity) AS field_maturity
    FROM dim_field
    GROUP BY 1
)
SELECT
    wc.short_name,
    mat.field_maturity,
    h.hc_mar21,
    h.hc_mar26,
    h.hc_mar26 - h.hc_mar21 AS hc_change,
    ROUND(p.mmboe_fy21, 2) AS mmboe_fy21,
    ROUND(p.mmboe_fy26, 2) AS mmboe_fy26,
    ROUND((p.mmboe_fy26 - p.mmboe_fy21) * 100.0 / NULLIF(p.mmboe_fy21, 0), 1) AS boe_growth_pct,
    ROUND(p.oil_mmt_fy21, 3) AS oil_mmt_fy21,
    ROUND(p.oil_mmt_fy26, 3) AS oil_mmt_fy26,
    ROUND(p.gas_bcm_fy21, 3) AS gas_bcm_fy21,
    ROUND(p.gas_bcm_fy26, 3) AS gas_bcm_fy26
FROM hc h
JOIN dim_work_centre wc ON h.wc_id = wc.wc_id
LEFT JOIN prod p ON p.wc_id = h.wc_id
LEFT JOIN mat ON mat.wc_id = h.wc_id
ORDER BY hc_change DESC;
