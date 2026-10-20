-- Answer Key SQL: T1
-- Question: "Which fields lost money in FY26?" → "Why is Field X losing?" → "How many people work there, and what do they cost?" → "Draft a board note with options."
-- Type: chain
-- Semantic audit 2026-10-20: Result unchanged (only Champang lost money at PBT level in FY26; no field had negative EBITDA). Added line_type='field' filter (LOWER), dropped dead '2026' code, added context columns (maturity, lifting cost, root cause, fields evaluated).

SELECT
    pnl.field_id,
    f.name AS field_name,
    f.onshore_offshore,
    f.maturity,
    pnl.asset_wc_id,
    pnl.fiscal_year,
    pnl.gross_revenue_inr_cr,
    pnl.total_opex_inr_cr,
    pnl.ebitda_inr_cr,
    pnl.dda_depreciation_inr_cr,
    pnl.pbt_inr_cr,
    pnl.lifting_cost_per_boe_usd,
    pnl.root_cause_loss_code,
    pnl.is_loss_making_3yr_consecutive,
    (SELECT COUNT(*) FROM field_pnl_annual x WHERE x.fiscal_year = 'FY26' AND LOWER(x.line_type) = 'field') AS fields_evaluated
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
WHERE pnl.fiscal_year = 'FY26'
  AND LOWER(pnl.line_type) = 'field'
  AND (pnl.pbt_inr_cr < 0 OR pnl.ebitda_inr_cr < 0)
ORDER BY pnl.pbt_inr_cr ASC;
