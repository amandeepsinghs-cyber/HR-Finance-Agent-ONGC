-- Answer Key Follow-up SQL: C6__why
-- Question: What are the primary cost drivers (e.g. high water cut, power costs, workover frequency, aging surface facilities) behind the loss-making fields?
-- Type: data
-- Semantic audit 2026-10-20: old SQL listed average water cut for all 53 fields with no cost data and no link
-- to the loss-makers. FY26 has only one PBT-negative field, so the set is the five lowest-PBT fields of FY26
-- (the loss-maker plus the four closest to breakeven) against the average of all FY26 fields. Cost components
-- are normalised per BOE in rupees (component_cr * 1e7 / BOE) so fields of different size are comparable;
-- water cut is the production-weighted FY26 average from production_monthly.

WITH wc AS (
    SELECT field_id,
           SUM(water_cut_pct * total_production_boe) / NULLIF(SUM(total_production_boe), 0) AS water_cut_pct
    FROM production_monthly
    WHERE fiscal_year = 'FY26'
    GROUP BY field_id
),
p AS (
    SELECT pnl.*, f.name AS field_name, wc.water_cut_pct,
           RANK() OVER (ORDER BY pnl.pbt_inr_cr ASC) AS pbt_rank
    FROM field_pnl_annual pnl
    JOIN dim_field f ON pnl.field_id = f.field_id
    LEFT JOIN wc ON wc.field_id = pnl.field_id
    WHERE pnl.fiscal_year = 'FY26' AND LOWER(pnl.line_type) = 'field'
),
u AS (
    SELECT field_name, pbt_rank AS ord, pbt_inr_cr, total_production_boe AS boe, water_cut_pct,
           allocated_manpower_cost_inr_cr AS mp, power_fuel_cost_inr_cr AS pw, workover_repairs_cost_inr_cr AS wo,
           water_handling_cost_inr_cr AS wh, logistics_osv_chopper_cost_inr_cr AS lg,
           chemicals_consumables_cost_inr_cr AS ch, contractor_cost_inr_cr AS ct, other_opex_inr_cr AS ot,
           total_opex_inr_cr AS tot, root_cause_loss_code
    FROM p WHERE pbt_rank <= 5
    UNION ALL
    SELECT 'All FY26 fields (total PBT, per-BOE weighted average)', 99, SUM(pbt_inr_cr), SUM(total_production_boe),
           SUM(water_cut_pct * total_production_boe) / NULLIF(SUM(total_production_boe), 0),
           SUM(allocated_manpower_cost_inr_cr), SUM(power_fuel_cost_inr_cr), SUM(workover_repairs_cost_inr_cr),
           SUM(water_handling_cost_inr_cr), SUM(logistics_osv_chopper_cost_inr_cr),
           SUM(chemicals_consumables_cost_inr_cr), SUM(contractor_cost_inr_cr), SUM(other_opex_inr_cr),
           SUM(total_opex_inr_cr), NULL
    FROM p
)
SELECT
    field_name,
    ROUND(pbt_inr_cr, 2) AS pbt_inr_cr,
    ROUND(water_cut_pct, 1) AS water_cut_pct,
    ROUND(tot * 1e7 / NULLIF(boe, 0), 0) AS opex_inr_per_boe,
    ROUND(mp * 1e7 / NULLIF(boe, 0), 0) AS manpower_inr_per_boe,
    ROUND(pw * 1e7 / NULLIF(boe, 0), 0) AS power_fuel_inr_per_boe,
    ROUND(wo * 1e7 / NULLIF(boe, 0), 0) AS workover_inr_per_boe,
    ROUND(wh * 1e7 / NULLIF(boe, 0), 0) AS water_handling_inr_per_boe,
    ROUND(ch * 1e7 / NULLIF(boe, 0), 0) AS chemicals_inr_per_boe,
    ROUND(ct * 1e7 / NULLIF(boe, 0), 0) AS contractor_inr_per_boe,
    ROUND((lg + ot) * 1e7 / NULLIF(boe, 0), 0) AS logistics_other_inr_per_boe,
    root_cause_loss_code
FROM u
ORDER BY ord;
