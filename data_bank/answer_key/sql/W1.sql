-- Answer Key SQL: W1
-- Question: If Brent falls to $60/bbl, which fields go into loss?
-- Type: what_if

WITH price_params AS (
    SELECT
        AVG(brent_usd_bbl) AS avg_brent,
        AVG(ongc_crude_net_realisation_usd_bbl) AS avg_realisation,
        AVG(brent_usd_bbl - ongc_crude_net_realisation_usd_bbl) AS avg_discount
    FROM `ongc-hr-finance-agent.hrfin_silver.price_fx_monthly`
    WHERE fiscal_year IN ('FY26', '2026')
),
sim_brent60 AS (
    SELECT
        pnl.field_id,
        f.name AS field_name,
        f.onshore_offshore,
        pnl.gross_revenue_inr_cr AS base_revenue_cr,
        pnl.total_opex_inr_cr AS base_opex_cr,
        pnl.dda_depreciation_inr_cr AS base_dda_cr,
        (pnl.oil_revenue_inr_cr * ((60.0 - params.avg_discount) / params.avg_realisation) + pnl.gas_revenue_inr_cr) AS sim_gross_rev_cr,
        SAFE_DIVIDE(pnl.statutory_royalty_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0)) AS eff_royalty_rate,
        SAFE_DIVIDE(pnl.statutory_cess_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0)) AS eff_cess_rate
    FROM `ongc-hr-finance-agent.hrfin_silver.field_pnl_annual` pnl
    JOIN `ongc-hr-finance-agent.hrfin_silver.dim_field` f ON pnl.field_id = f.field_id
    CROSS JOIN price_params params
    WHERE pnl.fiscal_year IN ('FY26', '2026') AND pnl.line_type = 'field'
)
SELECT
    field_id,
    field_name,
    onshore_offshore,
    ROUND(sim_gross_rev_cr, 2) AS sim_gross_revenue_inr_cr,
    ROUND(base_opex_cr, 2) AS total_opex_inr_cr,
    ROUND(sim_gross_rev_cr * (1.0 - eff_royalty_rate - eff_cess_rate) - base_opex_cr, 2) AS sim_ebitda_inr_cr,
    ROUND(sim_gross_rev_cr * (1.0 - eff_royalty_rate - eff_cess_rate) - base_opex_cr - base_dda_cr, 2) AS sim_pbt_inr_cr,
    CASE WHEN (sim_gross_rev_cr * (1.0 - eff_royalty_rate - eff_cess_rate) - base_opex_cr) < 0 THEN TRUE ELSE FALSE END AS is_ebitda_negative,
    CASE WHEN (sim_gross_rev_cr * (1.0 - eff_royalty_rate - eff_cess_rate) - base_opex_cr - base_dda_cr) < 0 THEN TRUE ELSE FALSE END AS is_pbt_negative
FROM sim_brent60
ORDER BY sim_pbt_inr_cr ASC;
