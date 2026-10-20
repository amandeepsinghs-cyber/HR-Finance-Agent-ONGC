-- Probe ID: C9.compare_or_so_what
-- Parent ID: C9
-- Answer Type: sql
-- Question: How does the anticipated final cost compare against the original Board-sanctioned budget and subsequent Revised Cost Estimates (RCE)?
-- Personas: CMD
-- Tables: project_progress, dim_project
-- Drill Dims: dim_project.name
-- Story IDs: S9
-- Expected Output: table
-- Handcrafted: true

SELECT
    p.name AS project_name,
    prg.original_sanctioned_cost_inr_cr,
    prg.revised_cost_estimate_rce_inr_cr,
    prg.revised_cost_inr_cr AS anticipated_final_cost_cr,
    ROUND(prg.revised_cost_inr_cr - prg.original_sanctioned_cost_inr_cr, 2) AS variance_from_original_cr
FROM project_progress prg
JOIN dim_project p ON prg.prj_id = p.prj_id
WHERE prg.original_sanctioned_cost_inr_cr IS NOT NULL
ORDER BY variance_from_original_cr DESC
LIMIT 50;
