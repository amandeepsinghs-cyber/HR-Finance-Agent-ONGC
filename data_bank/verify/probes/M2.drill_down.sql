-- Probe ID: M2.drill_down
-- Parent ID: M2
-- Answer Type: sql
-- Question: What is the year-to-date capex spend compared to Budget Estimates (BE) across major producing assets?
-- Personas: E1–E4 Officer (Finance)
-- Tables: capex_budget, dim_work_centre
-- Drill Dims: dim_work_centre.name
-- Story IDs: S9
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc.name,
    SUM(cb.budget_estimate_be_inr_cr) AS be_budget_cr,
    SUM(cb.actual_spend_inr_cr) AS ytd_actual_spend_cr
FROM capex_budget cb
JOIN dim_work_centre wc ON cb.asset_wc_id = wc.wc_id
WHERE cb.fiscal_year IN ('FY26', '2026')
GROUP BY wc.name
ORDER BY ytd_actual_spend_cr DESC;
