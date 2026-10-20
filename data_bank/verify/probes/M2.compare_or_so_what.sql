-- Probe ID: M2.compare_or_so_what
-- Parent ID: M2
-- Answer Type: sql
-- Question: How does this fiscal year's capex utilization rate compare with the previous 3-year average?
-- Personas: E1–E4 Officer (Finance)
-- Tables: capex_budget, dim_work_centre
-- Drill Dims: dim_work_centre.short_name
-- Story IDs: S9
-- Expected Output: chart
-- Handcrafted: true

SELECT
    wc.short_name,
    ROUND(SUM(CASE WHEN cb.fiscal_year IN ('FY26', '2026') THEN cb.actual_spend_inr_cr ELSE 0 END) * 100.0 /
          NULLIF(SUM(CASE WHEN cb.fiscal_year IN ('FY26', '2026') THEN cb.budget_estimate_be_inr_cr ELSE 0 END), 0), 1) AS fy26_utilisation_pct
FROM capex_budget cb
JOIN dim_work_centre wc ON cb.asset_wc_id = wc.wc_id
GROUP BY wc.short_name
ORDER BY fy26_utilisation_pct DESC;
