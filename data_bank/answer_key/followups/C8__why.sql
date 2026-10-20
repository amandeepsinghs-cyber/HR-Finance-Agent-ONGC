-- Answer Key Follow-up SQL: C8__why
-- Question: What technical operating constraints make in-house secondary/tertiary recovery uneconomic compared to third-party PEC operators?
-- Type: data
-- Semantic audit 2026-10-20: old SQL was an exact copy of C6__why's old query (water cut of all 53 fields).
-- Now: the parent's candidate fields (FY26 mature fields loss-making or PEC/divestment-flagged) against the
-- all-field FY26 benchmark on technical constraints: production-weighted water cut, water produced per BOE,
-- uptime and well downtime (production_monthly), lifting cost and manpower cost per BOE (USD, FY26) and BOE
-- per regular employee. Benchmark ratios are ratios of sums, not averages of field ratios.
-- GAP: there is no third-party PEC operator cost data; the comparison is in-house cost vs company norm.

WITH pm AS (
    SELECT field_id,
           SUM(water_cut_pct * total_production_boe) / NULLIF(SUM(total_production_boe), 0) AS water_cut_pct,
           SUM(water_produced_m3) AS water_m3,
           AVG(operational_uptime_pct) AS uptime_pct,
           SUM(well_downtime_hours) AS downtime_h
    FROM production_monthly
    WHERE fiscal_year = 'FY26'
    GROUP BY field_id
),
p AS (
    SELECT f.name AS field_name, pnl.*, pm.water_cut_pct, pm.water_m3, pm.uptime_pct, pm.downtime_h,
           (LOWER(f.maturity) = 'mature' AND (pnl.pbt_inr_cr < 0 OR pnl.is_divestment_candidate OR pnl.pec_monetisation_potential_flag)) AS is_candidate
    FROM field_pnl_annual pnl
    JOIN dim_field f ON pnl.field_id = f.field_id
    LEFT JOIN pm ON pm.field_id = pnl.field_id
    WHERE pnl.fiscal_year = 'FY26' AND LOWER(pnl.line_type) = 'field'
),
fx AS (SELECT AVG(inr_usd_fx_rate) AS fx FROM dim_price_fx WHERE fiscal_year = 'FY26'),
u AS (
    SELECT field_name, 0 AS ord, water_cut_pct, water_m3, uptime_pct, downtime_h, total_production_boe AS boe,
           total_opex_inr_cr AS opex, allocated_manpower_cost_inr_cr AS mp, regular_employee_headcount AS hc, root_cause_loss_code
    FROM p WHERE is_candidate
    UNION ALL
    SELECT 'All FY26 fields (benchmark)', 1,
           SUM(water_cut_pct * total_production_boe) / NULLIF(SUM(total_production_boe), 0),
           SUM(water_m3), AVG(uptime_pct), AVG(downtime_h), SUM(total_production_boe),
           SUM(total_opex_inr_cr), SUM(allocated_manpower_cost_inr_cr), SUM(regular_employee_headcount), NULL
    FROM p
)
SELECT
    u.field_name,
    ROUND(u.water_cut_pct, 1) AS water_cut_pct,
    ROUND(u.water_m3 * 6.2898 / NULLIF(u.boe, 0), 1) AS water_bbl_per_boe,
    ROUND(u.uptime_pct, 1) AS avg_uptime_pct,
    ROUND(u.downtime_h, 0) AS well_downtime_hours,
    ROUND(u.opex * 1e7 / NULLIF(u.boe, 0) / fx.fx, 2) AS lifting_cost_usd_boe,
    ROUND(u.mp * 1e7 / NULLIF(u.boe, 0) / fx.fx, 2) AS manpower_cost_usd_boe,
    ROUND(u.boe / NULLIF(u.hc, 0), 0) AS boe_per_regular_employee,
    u.root_cause_loss_code
FROM u CROSS JOIN fx
ORDER BY u.ord, lifting_cost_usd_boe DESC;
