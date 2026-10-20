-- Probe ID: F8.why
-- Parent ID: F8
-- Answer Type: sql
-- Question: Why have complex HP-HT and exploratory drilling dry holes elevated exploration costs in frontier basins?
-- Personas: Director (Finance)
-- Tables: wells_drilled
-- Drill Dims: wells_drilled.basin_name
-- Story IDs: S24
-- Expected Output: table
-- Handcrafted: true

SELECT
    w.basin_name,
    COUNT(w.well_id) AS dry_holes_count,
    ROUND(SUM(w.drilling_cost_inr_cr), 2) AS total_drilling_cost_cr
FROM wells_drilled w
WHERE LOWER(w.result_status) = 'dry_hole'
  AND w.fiscal_year IN ('FY26', '2026')
GROUP BY w.basin_name
ORDER BY dry_holes_count DESC;
