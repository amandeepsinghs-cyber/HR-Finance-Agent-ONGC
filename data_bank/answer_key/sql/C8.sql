-- Answer Key SQL: C8
-- Question: Which loss-making mature fields are candidates for divestment, a Production Enhancement Contract, or a marginal-field offer?
-- Type: data
-- Semantic audit 2026-10-20: old SQL returned FY26 PBT < 0 fields only (Champang) with no maturity filter and
-- ignored the candidate flags the question is about. Now: FY26 mature fields that are loss-making (PBT < 0)
-- OR carry a divestment / PEC-monetisation flag in field_pnl_annual, with FY24-FY26 cumulative PBT, the number
-- of loss years in that window, production, and the route implied by the recorded flags.

WITH hist AS (
    SELECT field_id,
           SUM(pbt_inr_cr) AS pbt_fy24_fy26_cr,
           COUNTIF(pbt_inr_cr < 0) AS loss_years_fy24_fy26
    FROM field_pnl_annual
    WHERE fiscal_year IN ('FY24', 'FY25', 'FY26') AND LOWER(line_type) = 'field'
    GROUP BY field_id
)
SELECT
    f.name AS field_name,
    wc.short_name AS asset,
    ROUND(pnl.total_production_boe / 1e6, 2) AS mmboe_fy26,
    pnl.gross_revenue_inr_cr,
    pnl.total_opex_inr_cr,
    pnl.ebitda_inr_cr,
    pnl.pbt_inr_cr,
    ROUND(h.pbt_fy24_fy26_cr, 2) AS pbt_fy24_fy26_cr,
    h.loss_years_fy24_fy26,
    pnl.is_divestment_candidate,
    pnl.pec_monetisation_potential_flag,
    pnl.is_loss_making_3yr_consecutive,
    CASE WHEN pnl.is_divestment_candidate THEN 'Divestment'
         WHEN pnl.pec_monetisation_potential_flag THEN 'Production Enhancement Contract'
         ELSE 'Marginal-field offer (no flag recorded)' END AS route_from_flags,
    pnl.root_cause_loss_code
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
LEFT JOIN hist h ON h.field_id = pnl.field_id
WHERE pnl.fiscal_year = 'FY26'
  AND LOWER(pnl.line_type) = 'field'
  AND LOWER(f.maturity) = 'mature'
  AND (pnl.pbt_inr_cr < 0 OR pnl.is_divestment_candidate OR pnl.pec_monetisation_potential_flag)
ORDER BY pnl.pbt_inr_cr ASC;
