-- Answer Key Follow-up SQL: T1__drill_down
-- Question: Which specific offshore and onshore mature fields recorded negative operating earnings in FY26?
-- Type: chain
-- Semantic audit 2026-10-20: Old SQL repeated the parent filter (PBT<0 OR EBITDA<0) so it re-listed Champang, and 'negative operating earnings' (EBITDA<0) was never isolated.
-- Semantic audit 2026-10-20: Now: all FY26 mature fields (onshore and offshore) with EBITDA margin and explicit flags for negative EBITDA and negative PBT.

SELECT
    f.name AS field_name,
    f.onshore_offshore,
    pnl.ebitda_inr_cr,
    pnl.ebitda_margin_pct,
    pnl.pbt_inr_cr,
    pnl.ebitda_inr_cr < 0 AS negative_operating_earnings,
    pnl.pbt_inr_cr < 0 AS negative_pbt
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
WHERE pnl.fiscal_year = 'FY26'
  AND LOWER(pnl.line_type) = 'field'
  AND LOWER(f.maturity) = 'mature'
ORDER BY pnl.ebitda_margin_pct ASC;
