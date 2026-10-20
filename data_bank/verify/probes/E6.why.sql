-- Probe ID: E6.why
-- Parent ID: E6
-- Answer Type: sql_plus_rag
-- Question: Why are certain advanced technical courses restricted to officers with minimum field experience prerequisites?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: training_calendar
-- Drill Dims: training_calendar.programme_name
-- Story IDs: S18
-- Expected Output: table
-- Handcrafted: false

SELECT
    training_calendar.programme_name,
    training_calendar.prerequisite_experience_years AS prerequisite_experience_years
FROM training_calendar
WHERE training_calendar.prerequisite_experience_years > 0
ORDER BY training_calendar.programme_name
LIMIT 100;
