-- Answer Key Follow-up SQL: C10__why
-- Question: Why did Q2 natural gas production and development well drilling targets fall behind the DPE MoU milestone schedule?
-- Type: data
-- Semantic audit 2026-10-20: old SQL returned the gas MoU row for every year (FY25-FY27) with its static note
-- - no quarterly data, no wells. Now: Q2 FY27 (Jul-Sep 2026) gas production from production_monthly vs the
-- pro-rata quarterly MoU targets (FY27 Excellent / 4 and Very Good / 4), by asset with the change vs Q2 FY26,
-- plus a company row. GAP: wells_drilled has no FY27 records (fy27_wells_recorded = 0), so the development-
-- well part of the question cannot be measured.

WITH g AS (
    SELECT asset_wc_id,
           SUM(IF(month IN ('2026-07', '2026-08', '2026-09'), gas_production_mmscm, 0)) / 1e3 AS q2_fy27_bcm,
           SUM(IF(month IN ('2026-04', '2026-05', '2026-06'), gas_production_mmscm, 0)) / 1e3 AS q1_fy27_bcm,
           SUM(IF(month IN ('2025-07', '2025-08', '2025-09'), gas_production_mmscm, 0)) / 1e3 AS q2_fy26_bcm
    FROM production_monthly
    WHERE month IN ('2025-07', '2025-08', '2025-09', '2026-04', '2026-05', '2026-06', '2026-07', '2026-08', '2026-09')
    GROUP BY asset_wc_id
),
t AS (
    SELECT excellent_target / 4 AS excellent_q_bcm, very_good_target / 4 AS very_good_q_bcm
    FROM mou_targets WHERE fiscal_year = 'FY27' AND parameter_id = 'MOU-GAS-PROD'
),
w AS (SELECT COUNT(*) AS fy27_wells_recorded FROM wells_drilled WHERE fiscal_year = 'FY27'),
u AS (
    SELECT wc.short_name AS scope, 0 AS ord, g.q1_fy27_bcm, g.q2_fy27_bcm, g.q2_fy26_bcm
    FROM g JOIN dim_work_centre wc ON wc.wc_id = g.asset_wc_id
    UNION ALL
    SELECT 'Company total', 1, SUM(q1_fy27_bcm), SUM(q2_fy27_bcm), SUM(q2_fy26_bcm) FROM g
)
SELECT
    u.scope,
    ROUND(u.q1_fy27_bcm, 3) AS q1_fy27_bcm,
    ROUND(u.q2_fy27_bcm, 3) AS q2_fy27_bcm,
    ROUND(u.q2_fy26_bcm, 3) AS q2_fy26_bcm,
    ROUND(u.q2_fy27_bcm - u.q2_fy26_bcm, 3) AS q2_change_vs_fy26_bcm,
    ROUND((u.q2_fy27_bcm - u.q2_fy26_bcm) * 100.0 / NULLIF(u.q2_fy26_bcm, 0), 1) AS q2_change_pct,
    IF(u.ord = 1, ROUND(t.excellent_q_bcm, 3), NULL) AS mou_excellent_q_target_bcm,
    IF(u.ord = 1, ROUND(t.very_good_q_bcm, 3), NULL) AS mou_very_good_q_target_bcm,
    IF(u.ord = 1, ROUND(u.q2_fy27_bcm - t.excellent_q_bcm, 3), NULL) AS q2_gap_to_excellent_bcm,
    w.fy27_wells_recorded
FROM u CROSS JOIN t CROSS JOIN w
WHERE u.q2_fy26_bcm > 0 OR u.q2_fy27_bcm > 0
ORDER BY u.ord, q2_change_vs_fy26_bcm ASC;
