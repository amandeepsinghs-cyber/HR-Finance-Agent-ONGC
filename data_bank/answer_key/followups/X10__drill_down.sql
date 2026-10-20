-- Answer Key Follow-up SQL: X10__drill_down
-- Question: Which 3 specific projects experienced milestone delays, and what is the quantified impact on anticipated completion dates?
-- Type: data
-- Semantic audit 2026-10-20: Project grain (old SQL returned 54 milestone rows - each project's slippage repeated on 6 milestones -
-- ordered by name). One row per slipped project with scheduled vs anticipated completion and cost overrun.
WITH proj AS (
    SELECT p.prj_id, d.name AS project_name, d.status AS project_status,
        MAX(p.schedule_slippage_months) AS slippage_months,
        MAX(p.scheduled_completion_date) AS scheduled_completion,
        MAX(p.anticipated_or_actual_completion_date) AS anticipated_completion,
        MAX(p.cost_overrun_inr_cr) AS cost_overrun_cr,
        ANY_VALUE(p.delay_root_cause_category) AS delay_root_cause,
        COUNTIF(LOWER(p.milestone_status) = 'delayed_critical_path') AS critical_path_milestones_delayed
    FROM project_progress p
    JOIN dim_project d ON d.prj_id = p.prj_id
    WHERE p.schedule_slippage_months > 0
    GROUP BY p.prj_id, d.name, d.status
)
SELECT
    project_name,
    project_status,
    slippage_months,
    scheduled_completion,
    anticipated_completion,
    DATE_DIFF(anticipated_completion, scheduled_completion, DAY) AS completion_delay_days,
    ROUND(cost_overrun_cr, 1) AS cost_overrun_cr,
    delay_root_cause,
    critical_path_milestones_delayed
FROM proj
ORDER BY LOWER(project_status) = 'completed', slippage_months DESC, cost_overrun_cr DESC;
