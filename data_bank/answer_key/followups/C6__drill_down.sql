-- Answer Key Follow-up SQL: C6__drill_down
-- Question: What were the individual net margins and EBITDA of mature onshore fields in Assam and Cauvery in FY26?
-- Type: data
-- Semantic audit 2026-10-20: old SQL had no asset/maturity filter - it returned all 53 fields (offshore
-- included) and no net margin. Now: FY26 mature onshore fields of Assam Asset, Jorhat Asset (both in Assam)
-- and Cauvery Asset, with EBITDA, EBITDA margin and net (PBT) margin on gross revenue.

SELECT
    wc.short_name AS asset,
    f.name AS field_name,
    pnl.gross_revenue_inr_cr,
    pnl.ebitda_inr_cr,
    ROUND(pnl.ebitda_inr_cr * 100.0 / NULLIF(pnl.gross_revenue_inr_cr, 0), 1) AS ebitda_margin_pct,
    pnl.pbt_inr_cr,
    ROUND(pnl.pbt_inr_cr * 100.0 / NULLIF(pnl.gross_revenue_inr_cr, 0), 1) AS net_margin_pct
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
WHERE pnl.fiscal_year = 'FY26'
  AND LOWER(pnl.line_type) = 'field'
  AND pnl.asset_wc_id IN ('WC-ASM', 'WC-JOR', 'WC-CAU')
  AND LOWER(f.maturity) = 'mature'
  AND LOWER(f.onshore_offshore) = 'onshore'
ORDER BY net_margin_pct ASC;
