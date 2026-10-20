-- Probe ID: E6
-- Parent ID: None
-- Answer Type: sql
-- Question: Which training programmes can I take this year?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: training_calendar, employee_master
-- Drill Dims: training_calendar.programme_name
-- Story IDs: S18
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 32.4 (company_avg_training_hours)
-- Expected Range: 29.16 - 35.64 (tolerance: ±10.0%)

SELECT
    programme_name,
    programme_id,
    institute,
    location_city,
    start_date,
    duration_days
FROM training_calendar
WHERE fiscal_year IN ('FY27', '2027')
ORDER BY start_date
LIMIT 100;
