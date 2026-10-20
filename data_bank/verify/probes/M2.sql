-- Probe ID: M2
-- Parent ID: None
-- Answer Type: sql
-- Question: "What is the capex utilisation by asset this year?" (aggregate)
-- Personas: E1–E4 Officer (Finance)
-- Tables: capex_budget, dim_work_centre
-- Drill Dims: dim_work_centre.name
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
