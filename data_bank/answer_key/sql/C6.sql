-- Answer Key SQL: C6
-- Question: Which fields or assets were the most profitable and which made losses in FY26?
-- Type: data
-- Semantic audit 2026-10-20: result unchanged in substance (the inner join to dim_field already excluded the
-- non-field P&L lines). Hygiene: explicit LOWER(line_type) = 'field', dropped the never-matching '2026'
-- fiscal-year alternate, added PBT margin and a loss flag so "which made losses" is explicit (FY26: 53 fields).

SELECT
    f.name AS field_name,
    wc.short_name AS asset,
    f.onshore_offshore,
    f.maturity,
    pnl.gross_revenue_inr_cr,
    pnl.total_opex_inr_cr,
    pnl.ebitda_inr_cr,
    pnl.pbt_inr_cr,
    ROUND(pnl.pbt_inr_cr * 100.0 / NULLIF(pnl.gross_revenue_inr_cr, 0), 1) AS pbt_margin_pct,
    pnl.pbt_inr_cr < 0 AS is_loss_making
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
WHERE pnl.fiscal_year = 'FY26'
  AND LOWER(pnl.line_type) = 'field'
ORDER BY pnl.pbt_inr_cr DESC;
