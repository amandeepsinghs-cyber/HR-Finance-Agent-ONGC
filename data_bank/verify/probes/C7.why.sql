-- Probe ID: C7.why
-- Parent ID: C7
-- Answer Type: sql_plus_rag
-- Question: Why did fields with substantial 2P oil/gas reserves receive less development drilling capex than planned in the BE/RE cycles?
-- Personas: CMD
-- Tables: capex_budget, reserves_annual, dim_field
-- Drill Dims: dim_field.name
-- Story IDs: S9
-- Expected Output: table
-- Handcrafted: true

SELECT
    f.name,
    SUM(r.reserves_2p_oil_mmt + r.reserves_2p_gas_bcm) AS total_2p_reserves_mmtoe,
    ROUND(AVG(r.development_cost_usd_per_boe), 2) AS avg_dev_cost_usd_boe
FROM reserves_annual r
JOIN dim_field f ON r.field_id = f.field_id
WHERE r.fiscal_year IN ('FY26', '2026')
GROUP BY f.name
ORDER BY total_2p_reserves_mmtoe DESC
LIMIT 20;
