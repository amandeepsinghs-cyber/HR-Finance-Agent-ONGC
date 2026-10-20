-- Probe ID: W1.drill_down
-- Parent ID: W1
-- Answer Type: what_if_sim
-- Question: Which 6 mature fields transition from marginal profitability to negative operating cash flow at 0 Brent?
-- Personas: CMD, Director (Finance)
-- Tables: field_pnl_annual, dim_field, production_monthly, price_fx_monthly
-- Drill Dims: dim_field.name
-- Story IDs: S15
-- Expected Output: table
-- Handcrafted: true

WITH field_sim AS (
    SELECT
        p.field_id,
        f.name AS field_name,
        SUM(p.oil_production_mt) * 7.33 AS oil_bbl,
        SUM(p.gas_production_mmscm) * 35.3147 AS gas_mmbtu,
        fx.inr_usd_fx_rate AS fx_rate,
        COALESCE(pnl.total_opex_inr_cr, 50.0) AS opex_cr,
        ((SUM(p.oil_production_mt) * 7.33 * 58.0 * fx.inr_usd_fx_rate) / 10000000.0) +
        ((SUM(p.gas_production_mmscm) * 35.3147 * 6.50 * fx.inr_usd_fx_rate) / 10000000.0) AS sim_gross_rev_cr,
        (((SUM(p.oil_production_mt) * 7.33 * 58.0 * fx.inr_usd_fx_rate) / 10000000.0) * 0.30) AS sim_levies_cr
    FROM production_monthly p
    JOIN dim_field f ON p.field_id = f.field_id
    LEFT JOIN field_pnl_annual pnl ON p.field_id = pnl.field_id AND pnl.fiscal_year IN ('FY26', '2026')
    CROSS JOIN (SELECT inr_usd_fx_rate FROM price_fx_monthly WHERE fiscal_year IN ('FY26', '2026') LIMIT 1) fx
    WHERE p.fiscal_year IN ('FY26', '2026')
    GROUP BY p.field_id, f.name, fx.inr_usd_fx_rate, pnl.total_opex_inr_cr
)
SELECT
    field_name,
    ROUND(sim_gross_rev_cr - sim_levies_cr - opex_cr, 2) AS sim_ebitda_cr
FROM field_sim
WHERE (sim_gross_rev_cr - sim_levies_cr - opex_cr) < 0
ORDER BY sim_ebitda_cr ASC
LIMIT 6;
