-- Answer Key Follow-up SQL: C9__drill_down
-- Question: What is the current schedule slippage and cost overrun on the KG-DWN-98/2 development and Western Offshore pipeline replacement projects?
-- Type: data
-- Semantic audit 2026-10-20: old SQL used case-sensitive LIKE '%KG%' / '%Pipeline%' / '%PRP%' (also catching
-- the onshore KG gas facility and the Tripura evacuation pipeline) and returned each project 6 times (one per
-- milestone). Now one row per project for KG-DWN-98/2 (PRJ-0001) and the Western Offshore pipeline
-- replacement projects (pipeline category, name contains 'replacement'), with planned vs revised completion.

WITH p AS (
    SELECT pp.prj_id,
           ANY_VALUE(pp.sanctioned_cost_inr_cr) AS sanctioned_cost_inr_cr,
           ANY_VALUE(pp.revised_cost_inr_cr) AS revised_cost_inr_cr,
           ANY_VALUE(pp.schedule_slippage_months) AS schedule_slippage_months,
           ANY_VALUE(pp.delay_root_cause_category) AS delay_root_cause_category,
           COUNTIF(LOWER(pp.milestone_status) = 'delayed_critical_path') AS delayed_milestones,
           MAX(pp.physical_progress_pct) AS max_milestone_progress_pct
    FROM project_progress pp
    GROUP BY pp.prj_id
)
SELECT
    d.name AS project_name,
    w.short_name AS asset,
    d.status,
    p.sanctioned_cost_inr_cr,
    p.revised_cost_inr_cr,
    ROUND(p.revised_cost_inr_cr - p.sanctioned_cost_inr_cr, 2) AS cost_overrun_cr,
    ROUND((p.revised_cost_inr_cr - p.sanctioned_cost_inr_cr) * 100.0 / NULLIF(p.sanctioned_cost_inr_cr, 0), 1) AS cost_overrun_pct,
    p.schedule_slippage_months,
    d.planned_completion,
    d.actual_or_revised_completion,
    p.delayed_milestones,
    p.delay_root_cause_category
FROM p
JOIN dim_project d ON d.prj_id = p.prj_id
JOIN dim_work_centre w ON w.wc_id = d.asset_wc_id
WHERE d.prj_id = 'PRJ-0001'
   OR (LOWER(d.category) = 'pipeline' AND LOWER(d.name) LIKE '%replacement%')
ORDER BY cost_overrun_cr DESC;
