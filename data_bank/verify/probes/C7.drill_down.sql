-- Probe ID: C7.drill_down
-- Parent ID: C7
-- Answer Type: sql
-- Question: What is the cumulative 5-year capex allocation across Western Offshore (MH, B&S) versus Eastern Offshore (KG Basin)?
-- Personas: CMD
-- Tables: capex_budget, dim_work_centre, dim_project
-- Drill Dims: dim_work_centre.name, capex_budget.fiscal_year
-- Story IDs: S9
-- Expected Output: chart
-- Handcrafted: true

SELECT
    wc.name,
    cb.fiscal_year,
    SUM(cb.actual_spend_inr_cr) AS total_actual_capex_cr
FROM capex_budget cb
JOIN dim_work_centre wc ON cb.asset_wc_id = wc.wc_id
WHERE cb.fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
GROUP BY wc.name, cb.fiscal_year
ORDER BY wc.name, cb.fiscal_year;
