-- Probe ID: X3.why
-- Parent ID: X3
-- Answer Type: sql
-- Question: What role does fatigue from extended shift overtime play in near-misses and Lost Time Injuries (LTI)?
-- Personas: CMD
-- Tables: hse_incidents
-- Drill Dims: hse_incidents.fatigue_factor_flag
-- Story IDs: S14
-- Expected Output: table
-- Handcrafted: false

SELECT
    hse_incidents.fatigue_factor_flag,
    COUNT(hse_incidents.incident_id) AS metric_1
FROM hse_incidents
WHERE hse_incidents.lost_time_injury_flag = TRUE
GROUP BY hse_incidents.fatigue_factor_flag
ORDER BY hse_incidents.fatigue_factor_flag
LIMIT 100;
