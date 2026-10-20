-- Probe ID: C9
-- Parent ID: None
-- Answer Type: sql
-- Question: Which major projects are behind schedule or over budget, and by how many crore?
-- Personas: CMD
-- Tables: project_progress, capex_budget, dim_project
-- Drill Dims: dim_project.name
-- Story IDs: S9
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 34012.0 (kg982_sanctioned_cost_cr)
-- Expected Range: 30610.8 - 37413.2 (tolerance: ±10.0%)

SELECT
    p.prj_id,
    p.name AS project_name,
    prg.sanctioned_cost_inr_cr,
    prg.revised_cost_inr_cr,
    ROUND(prg.revised_cost_inr_cr - prg.sanctioned_cost_inr_cr, 2) AS cost_overrun_cr,
    prg.schedule_slippage_months
FROM project_progress prg
JOIN dim_project p ON prg.prj_id = p.prj_id
WHERE (prg.revised_cost_inr_cr - prg.sanctioned_cost_inr_cr) > 0
ORDER BY cost_overrun_cr DESC;
