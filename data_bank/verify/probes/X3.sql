-- Probe ID: X3
-- Parent ID: None
-- Answer Type: sql
-- Question: Do assets with higher offshore overtime show a higher lost-time injury rate?
-- Personas: CMD
-- Tables: hse_incidents, dim_work_centre
-- Drill Dims: dim_work_centre.name
-- Story IDs: S14
-- Expected Output: table
-- Handcrafted: false
-- Story Target: 48.6 (neh_avg_monthly_overtime_hours)
-- Expected Range: 43.74 - 53.46 (tolerance: ±10.0%)

SELECT
    dim_work_centre.name,
    AVG(hse_incidents.monthly_overtime_hours_per_worker) AS metric_1,
    AVG(hse_incidents.calculated_ltifr) AS metric_2
FROM hse_incidents
LEFT JOIN dim_work_centre ON hse_incidents.wc_id = dim_work_centre.wc_id
WHERE hse_incidents.fiscal_year IN ('FY26', '2026')
GROUP BY dim_work_centre.name
ORDER BY dim_work_centre.name
LIMIT 100;
