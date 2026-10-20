-- Answer Key SQL: C9
-- Question: Which major projects are behind schedule or over budget, and by how many crore?
-- Type: data
-- Semantic audit 2026-10-20: project_progress has 6 milestone rows per project carrying the same project-level
-- cost and slippage, so the old SQL returned every project 6 times (360 rows) - any total over it is 6x.
-- Now one row per project (values are constant across milestones, verified), with overrun in crore and %,
-- slippage in months, a behind-schedule flag and the count of milestones on the delayed critical path.

WITH p AS (
    SELECT
        pp.prj_id,
        ANY_VALUE(pp.sanctioned_cost_inr_cr) AS sanctioned_cost_inr_cr,
        ANY_VALUE(pp.revised_cost_inr_cr) AS revised_cost_inr_cr,
        ANY_VALUE(pp.schedule_slippage_months) AS schedule_slippage_months,
        COUNTIF(LOWER(pp.milestone_status) = 'delayed_critical_path') AS delayed_milestones
    FROM project_progress pp
    GROUP BY pp.prj_id
)
SELECT
    p.prj_id,
    d.name AS project_name,
    d.status,
    p.sanctioned_cost_inr_cr,
    p.revised_cost_inr_cr,
    ROUND(p.revised_cost_inr_cr - p.sanctioned_cost_inr_cr, 2) AS cost_overrun_cr,
    ROUND((p.revised_cost_inr_cr - p.sanctioned_cost_inr_cr) * 100.0 / NULLIF(p.sanctioned_cost_inr_cr, 0), 1) AS cost_overrun_pct,
    p.schedule_slippage_months,
    p.schedule_slippage_months > 0 AS behind_schedule,
    p.delayed_milestones
FROM p
JOIN dim_project d ON d.prj_id = p.prj_id
WHERE p.revised_cost_inr_cr > p.sanctioned_cost_inr_cr OR p.schedule_slippage_months > 0
ORDER BY cost_overrun_cr DESC;
