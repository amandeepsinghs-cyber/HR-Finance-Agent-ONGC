-- Probe ID: E6.compare_or_so_what
-- Parent ID: E6
-- Answer Type: sql
-- Question: How do the mandatory technical training credits compare against managerial and leadership module requirements?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: training_calendar
-- Drill Dims: training_calendar.category
-- Story IDs: S18
-- Expected Output: table
-- Handcrafted: false

SELECT
    training_calendar.category,
    SUM(training_calendar.duration_days) AS metric_1
FROM training_calendar
GROUP BY training_calendar.category
ORDER BY training_calendar.category
LIMIT 100;
