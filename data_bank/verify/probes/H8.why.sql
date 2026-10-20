-- Probe ID: H8.why
-- Parent ID: H8
-- Answer Type: sql
-- Question: Why did executives in high-workload operational assets (Drilling, Offshore Production) achieve fewer training hours than target?
-- Personas: Director (HR)
-- Tables: training_records, posting_history, dim_discipline
-- Drill Dims: dim_discipline.name
-- Story IDs: S18
-- Expected Output: table
-- Handcrafted: false

SELECT
    dim_discipline.name,
    AVG(training_records.training_hours) AS metric_1
FROM training_records
LEFT JOIN posting_history ON posting_history.emp_id = training_records.emp_id
LEFT JOIN dim_discipline ON posting_history.discipline_id = dim_discipline.discipline_id
WHERE dim_discipline.name IN ('Drilling', 'Production') AND posting_history.posting_type = 'rotation'
GROUP BY dim_discipline.name
ORDER BY dim_discipline.name
LIMIT 100;
