-- Answer Key Follow-up SQL: W1__drill_down
-- Question: Which 6 mature fields transition from marginal profitability to negative operating cash flow at $60 Brent?
-- Type: what_if
-- Semantic audit 2026-10-20: Old SQL used sim PBT<0 as 'negative operating cash flow' - DD&A is non-cash, so operating cash flow is proxied by EBITDA; 3 fields listed vs 2 that actually turn cash-negative.
-- Semantic audit 2026-10-20: Now: same W1 formula (test_08), mature fields whose simulated EBITDA or PBT turns negative at $60, with separate cash-negative (EBITDA) and PBT-negative flags.

WITH price_params AS (
    SELECT
        AVG(brent_usd_bbl) AS avg_brent,
        AVG(ongc_crude_net_realisation_usd_bbl) AS avg_realisation,
        AVG(brent_usd_bbl - ongc_crude_net_realisation_usd_bbl) AS avg_discount,
        AVG(inr_usd_fx_rate) AS avg_fx
    FROM `ongc-hr-finance-agent.hrfin_silver.price_fx_monthly`
    WHERE fiscal_year = 'FY26'
),
sim AS (
    SELECT
        f.name AS field_name,
        f.onshore_offshore,
        pnl.ebitda_inr_cr AS base_ebitda_cr,
        pnl.ebitda_margin_pct AS base_ebitda_margin_pct,
        pnl.pbt_inr_cr AS base_pbt_cr,
        (pnl.oil_revenue_inr_cr * ((60.0 - params.avg_discount) / params.avg_realisation) + pnl.gas_revenue_inr_cr) * (1.0 - SAFE_DIVIDE(pnl.statutory_royalty_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0)) - SAFE_DIVIDE(pnl.statutory_cess_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0))) - pnl.total_opex_inr_cr AS sim_ebitda_cr,
        (pnl.oil_revenue_inr_cr * ((60.0 - params.avg_discount) / params.avg_realisation) + pnl.gas_revenue_inr_cr) * (1.0 - SAFE_DIVIDE(pnl.statutory_royalty_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0)) - SAFE_DIVIDE(pnl.statutory_cess_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0))) - pnl.total_opex_inr_cr - pnl.dda_depreciation_inr_cr AS sim_pbt_cr
    FROM `ongc-hr-finance-agent.hrfin_silver.field_pnl_annual` pnl
    JOIN `ongc-hr-finance-agent.hrfin_silver.dim_field` f ON pnl.field_id = f.field_id
    CROSS JOIN price_params params
    WHERE pnl.fiscal_year = 'FY26' AND LOWER(pnl.line_type) = 'field' AND LOWER(f.maturity) = 'mature'
)
SELECT
    field_name,
    onshore_offshore,
    ROUND(base_ebitda_cr, 2) AS base_ebitda_cr,
    ROUND(base_ebitda_margin_pct, 2) AS base_ebitda_margin_pct,
    ROUND(sim_ebitda_cr, 2) AS sim_ebitda_cr,
    ROUND(base_pbt_cr, 2) AS base_pbt_cr,
    ROUND(sim_pbt_cr, 2) AS sim_pbt_cr,
    sim_ebitda_cr < 0 AS turns_operating_cash_negative,
    sim_pbt_cr < 0 AS turns_pbt_negative
FROM sim
WHERE sim_ebitda_cr < 0 OR sim_pbt_cr < 0
ORDER BY sim_ebitda_cr ASC;
