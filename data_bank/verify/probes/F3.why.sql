-- Probe ID: F3.why
-- Parent ID: F3
-- Answer Type: sql
-- Question: What combination of oil price fluctuations, cess rates, and workover costs drove margin compression in mature onshore fields?
-- Personas: Director (Finance)
-- Tables: field_pnl_annual, dim_field
-- Drill Dims: dim_field.name
-- Story IDs: S6
-- Expected Output: table
-- Handcrafted: true

SELECT
    f.name AS field_name,
    ROUND(AVG(p.water_cut_pct), 2) AS avg_water_cut_pct
FROM production_monthly p
JOIN dim_field f ON p.field_id = f.field_id
WHERE p.fiscal_year IN ('FY26', '2026')
GROUP BY f.name
ORDER BY avg_water_cut_pct DESC;
