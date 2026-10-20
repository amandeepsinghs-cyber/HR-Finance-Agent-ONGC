-- Probe ID: C6.why
-- Parent ID: C6
-- Answer Type: sql
-- Question: What are the primary cost drivers (e.g. high water cut, power costs, workover frequency, aging surface facilities) behind the loss-making fields?
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
