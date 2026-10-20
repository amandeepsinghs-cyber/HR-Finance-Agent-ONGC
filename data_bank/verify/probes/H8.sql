-- Probe ID: H8
-- Parent ID: None
-- Answer Type: sql
-- Question: What were training hours per executive last year, and which disciplines are below target?
-- Personas: Director (HR)
-- Tables: training_records, employee_master, dim_discipline
-- Drill Dims: dim_discipline.name
-- Story IDs: S18
-- Expected Output: table
-- Handcrafted: false
-- Story Target: 32.4 (company_avg_training_hours)
-- Expected Range: 29.16 - 35.64 (tolerance: ±10.0%)

SELECT
    dim_discipline.name,
    AVG(training_records.training_hours) AS metric_1
FROM training_records
LEFT JOIN employee_master ON training_records.emp_id = employee_master.emp_id
LEFT JOIN dim_discipline ON employee_master.discipline_id = dim_discipline.discipline_id
WHERE training_records.fiscal_year IN ('FY26', '2026')
GROUP BY dim_discipline.name
ORDER BY dim_discipline.name
LIMIT 100;
