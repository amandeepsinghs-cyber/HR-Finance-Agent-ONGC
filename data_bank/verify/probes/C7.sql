-- Probe ID: C7
-- Parent ID: None
-- Answer Type: sql
-- Question: Where have we invested the most capex in the last 5 years, and which fields are under-invested relative to their reserves?
-- Personas: CMD
-- Tables: capex_budget, reserves_annual, dim_field, dim_project
-- Drill Dims: dim_field.name
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
