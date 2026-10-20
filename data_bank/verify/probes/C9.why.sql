-- Probe ID: C9.why
-- Parent ID: C9
-- Answer Type: sql_plus_rag
-- Question: What engineering, fabrication, or contractor delivery delays caused the milestone slippages across these projects?
-- Personas: CMD
-- Tables: project_progress, dim_project
-- Drill Dims: project_progress.delay_root_cause_category
-- Story IDs: S9
-- Expected Output: table
-- Handcrafted: true

SELECT
    delay_root_cause_category,
    COUNT(DISTINCT prj_id) AS affected_projects_count,
    ROUND(AVG(schedule_slippage_months), 1) AS avg_schedule_slippage_months,
    ROUND(SUM(cost_overrun_inr_cr), 2) AS total_cost_overrun_cr
FROM project_progress
WHERE schedule_slippage_months > 0
GROUP BY delay_root_cause_category
ORDER BY total_cost_overrun_cr DESC;
