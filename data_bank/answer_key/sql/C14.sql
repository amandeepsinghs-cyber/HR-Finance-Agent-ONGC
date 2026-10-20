-- Answer Key SQL: C14
-- Question: Prepare a one-page board note on the top 5 loss-making fields: production, cost, staffing and a recommendation.
-- Type: document
-- Semantic audit 2026-10-20: old SQL returned only revenue/opex/EBITDA/PBT for the five lowest-PBT fields - no
-- production, staffing or recommendation inputs - and the legacy board-note text called all five "top
-- operating losses" although only one (Champang) is PBT-negative in FY26. Now the five lowest-PBT FY26 fields
-- (field lines only) with production (MMboe), revenue, opex, manpower cost, EBITDA, PBT, regular and contract
-- headcount, lifting cost (USD/BOE, from field_pnl_annual), monetisation flags, root cause and the recorded
-- 5-year PEC/farm-out payoff, plus a loss flag so the note can state how many are actually loss-making.

SELECT
    f.name AS field_name,
    wc.short_name AS asset,
    f.maturity,
    ROUND(pnl.total_production_boe / 1e6, 2) AS mmboe_fy26,
    pnl.gross_revenue_inr_cr,
    pnl.total_opex_inr_cr,
    pnl.allocated_manpower_cost_inr_cr,
    pnl.ebitda_inr_cr,
    pnl.pbt_inr_cr,
    pnl.pbt_inr_cr < 0 AS is_loss_making,
    pnl.regular_employee_headcount,
    pnl.contractor_headcount,
    pnl.lifting_cost_per_boe_usd,
    pnl.manpower_cost_per_boe_usd,
    pnl.pec_monetisation_potential_flag,
    pnl.is_divestment_candidate,
    pnl.root_cause_loss_code,
    pnl.projected_pec_farmout_payoff_5yr_inr_cr
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
WHERE pnl.fiscal_year = 'FY26'
  AND LOWER(pnl.line_type) = 'field'
ORDER BY pnl.pbt_inr_cr ASC
LIMIT 5;
