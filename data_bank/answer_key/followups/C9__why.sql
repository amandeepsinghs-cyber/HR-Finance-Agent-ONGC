-- Answer Key Follow-up SQL: C9__why
-- Question: What engineering, fabrication, or contractor delivery delays caused the milestone slippages across these projects?
-- Type: data
-- Semantic audit 2026-10-20: JOIN_FANOUT - old SQL summed cost_overrun over 6 milestone rows per project
-- (e.g. subsea_commissioning 30,610.8 cr = 6 x 5,101.8) and averaged slippage over milestone rows. Now
-- project grain first (one row per project), restricted to projects that actually slipped, then grouped by the
-- recorded delay root cause, with the projects named and the count of milestones on the delayed critical path.

WITH p AS (
    SELECT pp.prj_id,
           ANY_VALUE(pp.delay_root_cause_category) AS delay_root_cause_category,
           ANY_VALUE(pp.schedule_slippage_months) AS schedule_slippage_months,
           ANY_VALUE(pp.revised_cost_inr_cr - pp.sanctioned_cost_inr_cr) AS cost_overrun_cr,
           COUNTIF(LOWER(pp.milestone_status) = 'delayed_critical_path') AS delayed_milestones,
           STRING_AGG(IF(LOWER(pp.milestone_status) = 'delayed_critical_path', pp.milestone_name, NULL), '; ' ORDER BY pp.milestone_id LIMIT 1) AS first_delayed_milestone
    FROM project_progress pp
    GROUP BY pp.prj_id
)
SELECT
    p.delay_root_cause_category,
    COUNT(*) AS projects_slipped,
    ROUND(AVG(p.schedule_slippage_months), 1) AS avg_slippage_months,
    MAX(p.schedule_slippage_months) AS max_slippage_months,
    ROUND(SUM(p.cost_overrun_cr), 2) AS cost_overrun_cr,
    SUM(p.delayed_milestones) AS delayed_critical_path_milestones,
    STRING_AGG(CONCAT(d.name, ' (', CAST(p.schedule_slippage_months AS STRING), ' m)'), '; ' ORDER BY p.schedule_slippage_months DESC) AS projects,
    STRING_AGG(DISTINCT p.first_delayed_milestone, '; ') AS first_delayed_milestones
FROM p
JOIN dim_project d ON d.prj_id = p.prj_id
WHERE p.schedule_slippage_months > 0
GROUP BY p.delay_root_cause_category
ORDER BY projects_slipped DESC, avg_slippage_months DESC;
