-- Probe ID: X8.compare_or_so_what
-- Parent ID: X8
-- Answer Type: sql
-- Question: What is our current RTI compliance and disposal rate compared to the statutory 30-day timeline mandated by the RTI Act?
-- Personas: CMD
-- Tables: rti_applications
-- Drill Dims: 
-- Story IDs: S19
-- Expected Output: number
-- Handcrafted: false

SELECT
    COUNT(CASE WHEN rti_applications.is_within_30_days_statutory = TRUE THEN 1 END) * 100.0 / COUNT(*) AS metric_1
FROM rti_applications
ORDER BY 1
LIMIT 100;
