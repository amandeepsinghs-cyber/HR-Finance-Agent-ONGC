-- Answer Key Follow-up SQL: W1__compare_or_so_what
-- Question: What would be the overall reduction in ONGC's annual EBITDA and operating cash flows if crude averages $60/bbl?
-- Type: what_if
-- Semantic audit 2026-10-20: Old SQL reported only field-level sums (field revenue 1,25,146 cr, field EBITDA 75,278 cr), not ONGC's annual EBITDA (63,284 cr) - overstating the base and hiding the % hit.
-- Semantic audit 2026-10-20: Now: field-level $60 impact plus company FY26 EBITDA from corporate_financials, simulated company EBITDA and % change. Pre-tax operating cash flow change = EBITDA change (opex fixed, no working-capital model); post-tax cash flow is not modelled (GAP).

WITH price_params AS (
    SELECT
        AVG(brent_usd_bbl) AS avg_brent,
        AVG(ongc_crude_net_realisation_usd_bbl) AS avg_realisation,
        AVG(brent_usd_bbl - ongc_crude_net_realisation_usd_bbl) AS avg_discount,
        AVG(inr_usd_fx_rate) AS avg_fx
    FROM `ongc-hr-finance-agent.hrfin_silver.price_fx_monthly`
    WHERE fiscal_year = 'FY26'
),
totals AS (
    SELECT
        SUM(pnl.gross_revenue_inr_cr) AS actual_rev,
        SUM(pnl.ebitda_inr_cr) AS actual_ebitda,
        SUM((pnl.oil_revenue_inr_cr * ((60.0 - params.avg_discount) / params.avg_realisation) + pnl.gas_revenue_inr_cr)) AS sim_rev,
        SUM((pnl.oil_revenue_inr_cr * ((60.0 - params.avg_discount) / params.avg_realisation) + pnl.gas_revenue_inr_cr) * (1.0 - SAFE_DIVIDE(pnl.statutory_royalty_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0)) - SAFE_DIVIDE(pnl.statutory_cess_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0))) - pnl.total_opex_inr_cr) AS sim_ebitda
    FROM `ongc-hr-finance-agent.hrfin_silver.field_pnl_annual` pnl
    CROSS JOIN price_params params
    WHERE pnl.fiscal_year = 'FY26' AND LOWER(pnl.line_type) = 'field'
),
corp AS (
    SELECT gross_revenue_inr_cr, ebitda_inr_cr
    FROM corporate_financials
    WHERE fiscal_year = 'FY26'
)
SELECT
    ROUND(t.actual_rev, 2) AS field_gross_revenue_cr,
    ROUND(t.sim_rev, 2) AS sim_field_gross_revenue_cr,
    ROUND(t.sim_rev - t.actual_rev, 2) AS revenue_change_cr,
    ROUND(t.actual_ebitda, 2) AS field_ebitda_cr,
    ROUND(t.sim_ebitda, 2) AS sim_field_ebitda_cr,
    ROUND(t.sim_ebitda - t.actual_ebitda, 2) AS ebitda_change_cr,
    c.ebitda_inr_cr AS company_ebitda_fy26_cr,
    ROUND(c.ebitda_inr_cr + t.sim_ebitda - t.actual_ebitda, 2) AS sim_company_ebitda_cr,
    ROUND((t.sim_ebitda - t.actual_ebitda) * 100.0 / c.ebitda_inr_cr, 1) AS company_ebitda_change_pct,
    ROUND(t.sim_ebitda - t.actual_ebitda, 2) AS pretax_operating_cash_flow_change_cr
FROM totals t
CROSS JOIN corp c;
