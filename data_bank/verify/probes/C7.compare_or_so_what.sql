-- Probe ID: C7.compare_or_so_what
-- Parent ID: C7
-- Answer Type: sql
-- Question: How does the reserve replacement ratio (RRR) and capital intensity ($/BOE added) compare between KG-98/2 and Mumbai High Redevelopment?
-- Personas: CMD
-- Tables: reserves_annual, capex_budget, dim_field
-- Drill Dims: dim_field.basin
-- Story IDs: S9
-- Expected Output: table
-- Handcrafted: true

SELECT
    f.basin,
    ROUND(AVG(r.reserve_replacement_ratio_rrr_2p), 2) AS avg_rrr_2p,
    ROUND(AVG(r.development_cost_usd_per_boe), 2) AS avg_dev_cost_usd_boe
FROM reserves_annual r
JOIN dim_field f ON r.field_id = f.field_id
WHERE r.fiscal_year IN ('FY26', '2026')
GROUP BY f.basin
ORDER BY avg_rrr_2p DESC;
