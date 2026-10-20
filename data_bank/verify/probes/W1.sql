-- Probe ID: W1
-- Parent ID: None
-- Answer Type: what_if_sim
-- Question: If Brent falls to $60/bbl, which fields go into loss?
-- Personas: CMD, Director (Finance)
-- Tables: field_pnl_annual, production_monthly, price_fx_monthly, dim_field
-- Drill Dims: dim_field.name
-- Story IDs: S15
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 75.4 (baseline_brent_price_usd)
-- Expected Range: 67.86 - 82.94 (tolerance: ±10.0%)

WITH field_sim AS (
    SELECT
        p.field_id,
        f.name AS field_name,
        SUM(p.oil_production_mt) * 7.33 AS oil_bbl,
        SUM(p.gas_production_mmscm) * 35.3147 AS gas_mmbtu,
        fx.inr_usd_fx_rate AS fx_rate,
        COALESCE(pnl.total_opex_inr_cr, 50.0) AS opex_cr,
        -- Simulated gross revenue at $60 Brent ($58 net realization) and $6.50 APM gas
        ((SUM(p.oil_production_mt) * 7.33 * 58.0 * fx.inr_usd_fx_rate) / 10000000.0) +
        ((SUM(p.gas_production_mmscm) * 35.3147 * 6.50 * fx.inr_usd_fx_rate) / 10000000.0) AS sim_gross_rev_cr,
        -- Statutory royalty and cess (~30% of crude revenue)
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
    ROUND(sim_gross_rev_cr - sim_levies_cr - opex_cr, 2) AS sim_ebitda_cr,
    CASE WHEN (sim_gross_rev_cr - sim_levies_cr - opex_cr) < 0 THEN TRUE ELSE FALSE END AS is_loss_making_at_60
FROM field_sim
ORDER BY sim_ebitda_cr ASC;
