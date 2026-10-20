-- Probe ID: C8.why
-- Parent ID: C8
-- Answer Type: sql_plus_rag
-- Question: What technical operating constraints make in-house secondary/tertiary recovery uneconomic compared to third-party PEC operators?
-- Personas: CMD
-- Tables: field_pnl_annual, production_monthly, dim_field
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
