-- Probe ID: F7
-- Parent ID: None
-- Answer Type: sql
-- Question: What is the employee cost as a percentage of revenue, by asset, and how has it trended?
-- Personas: Director (Finance)
-- Tables: field_pnl_annual, dim_work_centre
-- Drill Dims: dim_work_centre.name, field_pnl_annual.fiscal_year
-- Story IDs: S8
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 358.4 (company_avg_employee_cost_per_boe)
-- Expected Range: 322.56 - 394.24 (tolerance: ±10.0%)

SELECT
    wc.name,
    pnl.fiscal_year,
    pnl.allocated_manpower_cost_inr_cr,
    ROUND((pnl.allocated_manpower_cost_inr_cr * 10000000.0) / NULLIF(pnl.gross_revenue_inr_cr * 10000000.0, 0) * 100.0, 2) AS manpower_cost_pct_revenue
FROM field_pnl_annual pnl
JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
WHERE pnl.fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
GROUP BY wc.name, pnl.fiscal_year, pnl.allocated_manpower_cost_inr_cr, pnl.gross_revenue_inr_cr
ORDER BY wc.name, pnl.fiscal_year;
