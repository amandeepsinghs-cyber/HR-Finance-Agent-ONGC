-- Probe ID: F2.drill_down
-- Parent ID: F2
-- Answer Type: sql
-- Question: Which offshore and onshore projects show the largest underspend or overspend against their Budget Estimates (BE)?
-- Personas: Director (Finance)
-- Tables: capex_budget, dim_project
-- Drill Dims: dim_project.name
-- Story IDs: S9
-- Expected Output: table
-- Handcrafted: true

SELECT
    p.name AS project_name,
    SUM(cb.budget_estimate_be_inr_cr) AS be_cr,
    SUM(cb.actual_spend_inr_cr) AS actual_spend_cr,
    ROUND(SUM(cb.actual_spend_inr_cr) - SUM(cb.budget_estimate_be_inr_cr), 2) AS variance_from_be_cr
FROM capex_budget cb
JOIN dim_project p ON cb.prj_id = p.prj_id
WHERE cb.fiscal_year IN ('FY26', '2026')
GROUP BY p.name
ORDER BY ABS(variance_from_be_cr) DESC;
