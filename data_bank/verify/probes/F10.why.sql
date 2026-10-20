-- Probe ID: F10.why
-- Parent ID: F10
-- Answer Type: sql
-- Question: What specific asset-level operating expense variations accounted for the quarterly EBITDA fluctuations?
-- Personas: Director (Finance)
-- Tables: field_pnl_annual, dim_work_centre
-- Drill Dims: dim_work_centre.name
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
