-- Probe ID: X3.drill_down
-- Parent ID: X3
-- Answer Type: sql
-- Question: Which offshore platforms in Mumbai High and Neelam-Heera recorded the highest monthly overtime hours per technician?
-- Personas: CMD
-- Tables: hse_incidents, dim_work_centre
-- Drill Dims: hse_incidents.installation_name
-- Story IDs: S14
-- Expected Output: table
-- Handcrafted: false

SELECT
    hse_incidents.installation_name,
    AVG(hse_incidents.monthly_overtime_hours_per_worker) AS metric_1
FROM hse_incidents
LEFT JOIN dim_work_centre ON hse_incidents.wc_id = dim_work_centre.wc_id
WHERE dim_work_centre.short_name IN ('Mumbai High', 'Neelam & Heera')
GROUP BY hse_incidents.installation_name
ORDER BY hse_incidents.installation_name
LIMIT 100;
