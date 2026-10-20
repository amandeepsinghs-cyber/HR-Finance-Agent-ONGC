-- Answer Key Follow-up SQL: C14__drill_down
-- Question: What are the exact FY26 financial figures (gross revenue, opex, manpower cost, net operating loss) for these 5 fields?
-- Type: document
-- Semantic audit 2026-10-20: old SQL returned EBITDA and margin for all 53 fields (not "these 5") and none of
-- the requested figures. Now: the parent's five lowest-PBT FY26 fields with gross revenue, statutory levies,
-- opex, of which manpower cost, EBITDA, DD&A and PBT (net operating result; negative = loss).

SELECT
    f.name AS field_name,
    pnl.gross_revenue_inr_cr,
    ROUND(pnl.gross_revenue_inr_cr - pnl.net_revenue_inr_cr, 2) AS statutory_levies_inr_cr,
    pnl.total_opex_inr_cr,
    pnl.allocated_manpower_cost_inr_cr AS manpower_cost_inr_cr,
    pnl.ebitda_inr_cr,
    pnl.dda_depreciation_inr_cr,
    pnl.pbt_inr_cr AS net_operating_result_inr_cr,
    pnl.pbt_inr_cr < 0 AS is_loss
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
WHERE pnl.fiscal_year = 'FY26'
  AND LOWER(pnl.line_type) = 'field'
ORDER BY pnl.pbt_inr_cr ASC
LIMIT 5;
