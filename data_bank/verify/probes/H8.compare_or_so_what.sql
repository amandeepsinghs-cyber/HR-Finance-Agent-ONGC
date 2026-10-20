-- Probe ID: H8.compare_or_so_what
-- Parent ID: H8
-- Answer Type: sql_plus_rag
-- Question: How does our training investment per employee compare with the target set in the MoU with DPE?
-- Personas: Director (HR)
-- Tables: training_records, mou_targets
-- Drill Dims: mou_targets.parameter_name
-- Story IDs: S18
-- Expected Output: table
-- Handcrafted: false

SELECT
    mou_targets.parameter_name,
    AVG(training_records.training_hours) AS metric_1,
    MAX(mou_targets.actual_achievement) AS actual_achievement
FROM training_records
LEFT JOIN mou_targets ON mou_targets.fiscal_year = training_records.fiscal_year
WHERE mou_targets.parameter_name = 'milestone_project_execution'
GROUP BY mou_targets.parameter_name
ORDER BY mou_targets.parameter_name
LIMIT 100;
