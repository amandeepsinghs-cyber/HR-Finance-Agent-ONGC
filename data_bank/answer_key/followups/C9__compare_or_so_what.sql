-- Answer Key Follow-up SQL: C9__compare_or_so_what
-- Question: How does the anticipated final cost compare against the original Board-sanctioned budget and subsequent Revised Cost Estimates (RCE)?
-- Type: data
-- Semantic audit 2026-10-20: JOIN_FANOUT - old SQL returned milestone rows (6 per project) and LIMIT 50 cut the
-- list after ~9 projects. Now one row per project plus a portfolio total: original Board-sanctioned cost, RCE,
-- anticipated final cost (revised_cost_inr_cr), variance vs original and vs RCE. Note: in the data the RCE
-- equals the anticipated final cost and original equals current sanctioned cost for every project.

WITH p AS (
    SELECT pp.prj_id,
           ANY_VALUE(pp.original_sanctioned_cost_inr_cr) AS original_sanctioned_cost_inr_cr,
           ANY_VALUE(pp.revised_cost_estimate_rce_inr_cr) AS rce_inr_cr,
           ANY_VALUE(pp.revised_cost_inr_cr) AS anticipated_final_cost_inr_cr
    FROM project_progress pp
    GROUP BY pp.prj_id
),
u AS (
    SELECT d.name AS project_name, 0 AS ord, p.original_sanctioned_cost_inr_cr, p.rce_inr_cr, p.anticipated_final_cost_inr_cr
    FROM p JOIN dim_project d ON d.prj_id = p.prj_id
    UNION ALL
    SELECT 'Portfolio total (60 projects)', 1, SUM(original_sanctioned_cost_inr_cr), SUM(rce_inr_cr), SUM(anticipated_final_cost_inr_cr) FROM p
)
SELECT
    project_name,
    original_sanctioned_cost_inr_cr,
    rce_inr_cr,
    anticipated_final_cost_inr_cr,
    ROUND(anticipated_final_cost_inr_cr - original_sanctioned_cost_inr_cr, 2) AS variance_vs_original_cr,
    ROUND((anticipated_final_cost_inr_cr - original_sanctioned_cost_inr_cr) * 100.0 / NULLIF(original_sanctioned_cost_inr_cr, 0), 1) AS variance_vs_original_pct,
    ROUND(anticipated_final_cost_inr_cr - rce_inr_cr, 2) AS variance_vs_rce_cr
FROM u
ORDER BY ord, variance_vs_original_cr DESC;
