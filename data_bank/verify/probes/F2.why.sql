-- Probe ID: F2.why
-- Parent ID: F2
-- Answer Type: sql_plus_rag
-- Question: What are the primary causes (vendor delays, scope changes, weather downtime) for variance between planned and actual capex?
-- Personas: Director (Finance)
-- Tables: project_progress, dim_project
-- Drill Dims: project_progress.delay_root_cause_category
-- Story IDs: S9
-- Expected Output: table
-- Handcrafted: true

SELECT
    delay_root_cause_category,
    COUNT(DISTINCT prj_id) AS projects_count,
    ROUND(SUM(cost_overrun_inr_cr), 2) AS total_cost_overrun_cr
FROM project_progress
WHERE cost_overrun_inr_cr > 0
GROUP BY delay_root_cause_category
ORDER BY total_cost_overrun_cr DESC;
