-- Probe ID: E6.drill_down
-- Parent ID: E6
-- Answer Type: sql
-- Question: What upcoming courses are scheduled at ONGC Academy Dehradun and IOGPT Navi Mumbai for my grade and discipline?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: training_calendar
-- Drill Dims: training_calendar.programme_name
-- Story IDs: S18
-- Expected Output: table
-- Handcrafted: false

SELECT
    training_calendar.programme_name,
    training_calendar.programme_name, training_calendar.start_date AS start_date
FROM training_calendar
WHERE training_calendar.institute IN ('ONGC_Academy_Dehradun', 'IOGPT_Navi_Mumbai')
ORDER BY training_calendar.programme_name
LIMIT 100;
