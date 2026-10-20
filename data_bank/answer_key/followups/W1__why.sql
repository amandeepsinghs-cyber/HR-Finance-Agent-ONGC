-- Answer Key Follow-up SQL: W1__why
-- Question: Why do high-lifting-cost onshore assets suffer greater financial vulnerability to crude price contractions?
-- Type: what_if
-- Semantic audit 2026-10-20: Old SQL averaged lifting cost unweighted, classified onshore/offshore by work centre, and compared absolute revenue loss (offshore larger) - it could not show vulnerability.
-- Semantic audit 2026-10-20: Now: field segments (onshore/offshore x lifting-cost band) with BOE-weighted lifting cost, base vs $60 EBITDA, % EBITDA erosion, simulated margin and fields going PBT-negative.

WITH price_params AS (
    SELECT
        AVG(brent_usd_bbl) AS avg_brent,
        AVG(ongc_crude_net_realisation_usd_bbl) AS avg_realisation,
        AVG(brent_usd_bbl - ongc_crude_net_realisation_usd_bbl) AS avg_discount,
        AVG(inr_usd_fx_rate) AS avg_fx
    FROM `ongc-hr-finance-agent.hrfin_silver.price_fx_monthly`
    WHERE fiscal_year = 'FY26'
),
f AS (
    SELECT
        fd.onshore_offshore,
        CASE WHEN pnl.lifting_cost_per_boe_usd >= 20 THEN '1 high (>= $20/boe)'
             WHEN pnl.lifting_cost_per_boe_usd >= 10 THEN '2 mid ($10-20/boe)'
             ELSE '3 low (< $10/boe)' END AS lifting_cost_band,
        pnl.total_opex_inr_cr,
        pnl.total_production_boe,
        pnl.ebitda_inr_cr AS base_ebitda,
        (pnl.oil_revenue_inr_cr * ((60.0 - params.avg_discount) / params.avg_realisation) + pnl.gas_revenue_inr_cr) AS sim_rev,
        (pnl.oil_revenue_inr_cr * ((60.0 - params.avg_discount) / params.avg_realisation) + pnl.gas_revenue_inr_cr) * (1.0 - SAFE_DIVIDE(pnl.statutory_royalty_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0)) - SAFE_DIVIDE(pnl.statutory_cess_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0))) - pnl.total_opex_inr_cr AS sim_ebitda,
        (pnl.oil_revenue_inr_cr * ((60.0 - params.avg_discount) / params.avg_realisation) + pnl.gas_revenue_inr_cr) * (1.0 - SAFE_DIVIDE(pnl.statutory_royalty_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0)) - SAFE_DIVIDE(pnl.statutory_cess_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0))) - pnl.total_opex_inr_cr - pnl.dda_depreciation_inr_cr AS sim_pbt,
        params.avg_fx
    FROM `ongc-hr-finance-agent.hrfin_silver.field_pnl_annual` pnl
    JOIN `ongc-hr-finance-agent.hrfin_silver.dim_field` fd ON fd.field_id = pnl.field_id
    CROSS JOIN price_params params
    WHERE pnl.fiscal_year = 'FY26' AND LOWER(pnl.line_type) = 'field'
)
SELECT
    onshore_offshore,
    lifting_cost_band,
    COUNT(*) AS n_fields,
    ROUND(SUM(total_opex_inr_cr) * 1e7 / ANY_VALUE(avg_fx) / NULLIF(SUM(total_production_boe), 0), 2) AS wtd_lifting_cost_usd_boe,
    ROUND(SUM(base_ebitda), 2) AS base_ebitda_cr,
    ROUND(SUM(sim_ebitda), 2) AS sim_ebitda_at_60_cr,
    ROUND((SUM(sim_ebitda) - SUM(base_ebitda)) * 100.0 / NULLIF(SUM(base_ebitda), 0), 1) AS ebitda_change_pct,
    ROUND(SUM(sim_ebitda) * 100.0 / NULLIF(SUM(sim_rev), 0), 1) AS sim_ebitda_margin_pct,
    COUNTIF(sim_pbt < 0) AS fields_pbt_negative_at_60
FROM f
GROUP BY onshore_offshore, lifting_cost_band
ORDER BY ebitda_change_pct ASC;
