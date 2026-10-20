-- Probe ID: X3.compare_or_so_what
-- Parent ID: X3
-- Answer Type: sql
-- Question: How does the safety incident frequency rate (LTIFR) in high-overtime assets compare with the corporate safety target?
-- Personas: CMD
-- Tables: hse_incidents, mou_targets
-- Drill Dims: 
-- Story IDs: S14
-- Expected Output: table
-- Handcrafted: false

SELECT
    AVG(hse_incidents.calculated_ltifr) AS metric_1,
    MAX(mou_targets.excellent_target) AS excellent_target
FROM hse_incidents
LEFT JOIN mou_targets ON hse_incidents.fiscal_year = mou_targets.fiscal_year
WHERE mou_targets.parameter_name = 'safety_ltifr_score'
ORDER BY 1
LIMIT 100;
