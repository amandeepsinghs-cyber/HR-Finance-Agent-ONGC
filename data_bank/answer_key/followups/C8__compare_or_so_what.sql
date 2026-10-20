-- Answer Key Follow-up SQL: C8__compare_or_so_what
-- Question: What would be the estimated capex and opex savings if the bottom 5 loss-making marginal fields are monetised or farmed out?
-- Type: data
-- Semantic audit 2026-10-20: old SQL listed EBITDA of all 53 fields and no savings at all. Now: the five
-- lowest-PBT FY26 fields (only one is PBT-negative in FY26) with the recorded estimated annual opex and capex
-- savings from field_pnl_annual, the FY26 opex, manpower cost and PBT given up, and a total row.
-- GAP: savings estimates exist only where the field carries a monetisation estimate; others show NULL.

WITH b AS (
    SELECT f.name AS field_name, wc.short_name AS asset, pnl.*,
           RANK() OVER (ORDER BY pnl.pbt_inr_cr ASC) AS pbt_rank
    FROM field_pnl_annual pnl
    JOIN dim_field f ON pnl.field_id = f.field_id
    JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
    WHERE pnl.fiscal_year = 'FY26' AND LOWER(pnl.line_type) = 'field'
),
u AS (
    SELECT field_name, asset, pbt_rank AS ord, pbt_inr_cr, total_opex_inr_cr, allocated_manpower_cost_inr_cr,
           estimated_annual_opex_savings_inr_cr, estimated_annual_capex_savings_inr_cr,
           COALESCE(estimated_annual_opex_savings_inr_cr, 0) + COALESCE(estimated_annual_capex_savings_inr_cr, 0) AS total_annual_savings_inr_cr,
           (estimated_annual_opex_savings_inr_cr IS NOT NULL) AS has_estimate
    FROM b WHERE pbt_rank <= 5
)
SELECT field_name, asset, ROUND(pbt_inr_cr, 2) AS pbt_fy26_inr_cr, ROUND(total_opex_inr_cr, 2) AS opex_fy26_inr_cr,
       ROUND(allocated_manpower_cost_inr_cr, 2) AS manpower_fy26_inr_cr,
       estimated_annual_opex_savings_inr_cr, estimated_annual_capex_savings_inr_cr,
       ROUND(total_annual_savings_inr_cr, 2) AS total_annual_savings_inr_cr, has_estimate
FROM (
    SELECT * FROM u
    UNION ALL
    SELECT 'Bottom-5 total', NULL, 99, SUM(pbt_inr_cr), SUM(total_opex_inr_cr), SUM(allocated_manpower_cost_inr_cr),
           SUM(estimated_annual_opex_savings_inr_cr), SUM(estimated_annual_capex_savings_inr_cr),
           SUM(total_annual_savings_inr_cr), LOGICAL_AND(has_estimate)
    FROM u
)
ORDER BY ord;
