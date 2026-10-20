-- Answer Key Follow-up SQL: T1__compare_or_so_what
-- Question: What is the net cost impact of divesting Field X versus investing in secondary recovery over a 5-year horizon?
-- Type: chain
-- Semantic audit 2026-10-20: Old SQL listed FY26 EBITDA for all 53 fields - no divest-vs-invest comparison and no Field X.
-- Semantic audit 2026-10-20: Now: Field X 5-year options - status quo (5 x FY26 PBT), divest/PEC farm-out payoff, annual savings, and the breakeven uplift a secondary-recovery programme must deliver. Field-level secondary-recovery cost/uplift is not in the data (GAP); asset secondary-recovery capex shown for reference.

WITH x AS (
    SELECT field_id
    FROM field_pnl_annual
    WHERE fiscal_year = 'FY26' AND LOWER(line_type) = 'field' AND pbt_inr_cr < 0
    ORDER BY pbt_inr_cr
    LIMIT 1
)
SELECT
    p.field_id,
    f.name AS field_name,
    p.asset_wc_id,
    p.gross_revenue_inr_cr AS fy26_revenue_inr_cr,
    p.ebitda_inr_cr AS fy26_ebitda_inr_cr,
    p.pbt_inr_cr AS fy26_pbt_inr_cr,
    ROUND(p.pbt_inr_cr * 5, 2) AS status_quo_5yr_pbt_inr_cr,
    p.projected_pec_farmout_payoff_5yr_inr_cr AS divest_pec_5yr_payoff_inr_cr,
    p.estimated_annual_opex_savings_inr_cr,
    p.estimated_annual_capex_savings_inr_cr,
    ROUND(p.projected_pec_farmout_payoff_5yr_inr_cr - p.pbt_inr_cr * 5, 2) AS divest_advantage_vs_status_quo_5yr_inr_cr,
    ROUND((p.projected_pec_farmout_payoff_5yr_inr_cr - p.pbt_inr_cr * 5) / 5, 2) AS breakeven_annual_pbt_uplift_for_secondary_recovery_inr_cr,
    ROUND((p.projected_pec_farmout_payoff_5yr_inr_cr - p.pbt_inr_cr * 5) / 5 * 100.0 / NULLIF(p.gross_revenue_inr_cr, 0), 1) AS breakeven_uplift_pct_of_fy26_revenue,
    p.is_divestment_candidate,
    p.pec_monetisation_potential_flag,
    (SELECT ROUND(SUM(c.secondary_recovery_capex_inr_cr), 2) FROM capex_budget c
      WHERE c.asset_wc_id = p.asset_wc_id AND c.fiscal_year = 'FY26') AS asset_secondary_recovery_capex_fy26_inr_cr
FROM field_pnl_annual p
JOIN dim_field f ON f.field_id = p.field_id
WHERE p.fiscal_year = 'FY26' AND LOWER(p.line_type) = 'field'
  AND p.field_id IN (SELECT field_id FROM x);
