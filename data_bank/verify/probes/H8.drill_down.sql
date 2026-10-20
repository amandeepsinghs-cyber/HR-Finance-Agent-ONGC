-- Probe ID: H8.drill_down
-- Parent ID: H8
-- Answer Type: sql
-- Question: What were the average training man-days completed at ONGC Academy (Dehradun), IOGPT, and KDMIPE by discipline?
-- Personas: Director (HR)
-- Tables: training_records, dim_discipline, employee_master
-- Drill Dims: training_records.institute, dim_discipline.name
-- Story IDs: S18
-- Expected Output: table
-- Handcrafted: true

SELECT
    training_records.institute,
    dim_discipline.name,
    AVG(training_records.training_days) AS metric_1
FROM training_records
JOIN employee_master ON training_records.emp_id = employee_master.emp_id
JOIN dim_discipline ON employee_master.discipline_id = dim_discipline.discipline_id
WHERE training_records.institute IN ('ONGC_Academy_Dehradun', 'IOGPT_Navi_Mumbai', 'KDMIPE')
GROUP BY training_records.institute, dim_discipline.name
ORDER BY training_records.institute, dim_discipline.name
LIMIT 100;
