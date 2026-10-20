-- Answer Key Follow-up SQL: F2__why
-- Question: Why have procurement delays, rig mobilization slippages, or environmental clearances slowed capex execution in Eastern Offshore?
-- Type: data
-- Semantic audit 2026-10-20: was company-wide (no Eastern Offshore filter) and summed the project-level cost overrun
-- Semantic audit 2026-10-20: over 6 milestone rows per project (6x fan-out: 44,601 cr). Now Eastern Offshore (WC-EAS)
-- Semantic audit 2026-10-20: projects at project grain: recorded delay root cause, slippage, overrun counted once,
-- Semantic audit 2026-10-20: delayed milestones, and FY27 YTD capex utilisation vs BE. GAP: project_progress only has 4
-- Semantic audit 2026-10-20: root-cause codes; none is procurement, rig mobilisation or environmental clearance.

WITH prj AS (
    SELECT
        pp.prj_id,
        ANY_VALUE(pp.delay_root_cause_category) AS delay_root_cause,
        MAX(pp.schedule_slippage_months) AS slippage_months,
        MAX(pp.sanctioned_cost_inr_cr) AS sanctioned_cost_cr,
        MAX(pp.revised_cost_inr_cr) AS revised_cost_cr,
        MAX(pp.cost_overrun_inr_cr) AS cost_overrun_cr,
        COUNTIF(LOWER(pp.milestone_status) LIKE 'delayed%') AS delayed_milestones,
        STRING_AGG(IF(LOWER(pp.milestone_status) LIKE 'delayed%', pp.milestone_name, NULL), '; ') AS delayed_milestone_names,
        ANY_VALUE(pp.brief_notes) AS notes
    FROM project_progress pp
    JOIN dim_project dp ON dp.prj_id = pp.prj_id
    WHERE dp.asset_wc_id = 'WC-EAS'
    GROUP BY pp.prj_id
),
cap AS (
    SELECT prj_id,
           SUM(budget_estimate_be_inr_cr) AS be_ytd,
           SUM(actual_spend_inr_cr) AS actual_ytd
    FROM capex_budget
    WHERE fiscal_year = 'FY27' AND asset_wc_id = 'WC-EAS'
    GROUP BY prj_id
)
SELECT
    p.prj_id,
    dp.name AS project_name,
    p.delay_root_cause,
    p.slippage_months,
    p.sanctioned_cost_cr,
    p.revised_cost_cr,
    p.cost_overrun_cr,
    p.delayed_milestones,
    p.delayed_milestone_names,
    ROUND(c.be_ytd, 1) AS fy27_be_ytd_cr,
    ROUND(c.actual_ytd, 1) AS fy27_actual_ytd_cr,
    ROUND(c.actual_ytd * 100 / NULLIF(c.be_ytd, 0), 1) AS fy27_utilisation_vs_be_pct,
    p.notes
FROM prj p
JOIN dim_project dp ON dp.prj_id = p.prj_id
LEFT JOIN cap c ON c.prj_id = p.prj_id
ORDER BY p.cost_overrun_cr DESC;
