-- Probe ID: X10.drill_down
-- Parent ID: X10
-- Answer Type: sql
-- Question: Which 3 specific projects experienced milestone delays, and what is the quantified impact on anticipated completion dates?
-- Personas: CMD
-- Tables: project_progress, dim_project
-- Drill Dims: dim_project.name
-- Story IDs: S36
-- Expected Output: table
-- Handcrafted: false

SELECT
    dim_project.name,
    project_progress.schedule_slippage_months AS schedule_slippage_months
FROM project_progress
LEFT JOIN dim_project ON project_progress.prj_id = dim_project.prj_id
WHERE project_progress.schedule_slippage_months > 0
ORDER BY dim_project.name
LIMIT 100;
