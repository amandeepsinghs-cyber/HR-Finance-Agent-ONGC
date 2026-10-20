-- Probe ID: C9.drill_down
-- Parent ID: C9
-- Answer Type: sql
-- Question: What is the current schedule slippage and cost overrun on the KG-DWN-98/2 development and Western Offshore pipeline replacement projects?
-- Personas: CMD
-- Tables: project_progress, dim_project
-- Drill Dims: dim_project.name
-- Story IDs: S9
-- Expected Output: table
-- Handcrafted: true

SELECT
    p.name AS project_name,
    prg.sanctioned_cost_inr_cr,
    prg.revised_cost_inr_cr,
    ROUND(prg.revised_cost_inr_cr - prg.sanctioned_cost_inr_cr, 2) AS cost_overrun_cr,
    prg.schedule_slippage_months
FROM project_progress prg
JOIN dim_project p ON prg.prj_id = p.prj_id
WHERE p.name LIKE '%KG%' OR p.name LIKE '%Pipeline%' OR p.name LIKE '%PRP%'
ORDER BY cost_overrun_cr DESC;
