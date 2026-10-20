-- Probe ID: C11.drill_down
-- Parent ID: C11
-- Answer Type: sql
-- Question: What is the specific 5-year headcount change and crude/gas output variance for Mehsana, Assam, and Rajahmundry assets?
-- Personas: CMD
-- Tables: headcount_snapshot, production_monthly, dim_work_centre
-- Drill Dims: headcount_snapshot.fiscal_year
-- Story IDs: S7
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc.short_name,
    h.fiscal_year,
    SUM(h.headcount) AS asset_headcount
FROM headcount_snapshot h
JOIN dim_work_centre wc ON h.wc_id = wc.wc_id
WHERE wc.wc_id IN ('WC-MEH', 'WC-ASM', 'WC-RAJ')
  AND h.fiscal_year IN ('FY21', 'FY26')
GROUP BY wc.short_name, h.fiscal_year
ORDER BY wc.short_name, h.fiscal_year;
