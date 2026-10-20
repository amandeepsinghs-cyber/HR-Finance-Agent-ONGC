-- Probe ID: X6.why
-- Parent ID: X6
-- Answer Type: sql
-- Question: What technical training programmes have been established at ONGC Academy to transition conventional engineers into renewable energy roles?
-- Personas: CMD
-- Tables: training_records
-- Drill Dims: training_records.programme_name
-- Story IDs: S34
-- Expected Output: table
-- Handcrafted: true

SELECT
    programme_name,
    COUNT(DISTINCT emp_id) AS engineers_reskilled,
    SUM(training_days) AS total_training_days
FROM training_records
WHERE is_renewable_reskilling = TRUE
GROUP BY programme_name
ORDER BY engineers_reskilled DESC
LIMIT 100;
