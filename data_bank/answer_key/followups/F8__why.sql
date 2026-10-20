-- Answer Key Follow-up SQL: F8__why
-- Question: Why have complex HP-HT and exploratory drilling dry holes elevated exploration costs in frontier basins?
-- Type: data
-- Semantic audit 2026-10-20: counted FY26 dry holes of all well types (development included) without well totals, so no
-- Semantic audit 2026-10-20: dry-hole rate or cost per well. Now exploratory wells FY24-FY26 (same 3-year window as the
-- Semantic audit 2026-10-20: drill-down) by basin and terrain: wells, dry holes, dry-hole rate, dry-hole cost, average cost
-- Semantic audit 2026-10-20: per exploratory well. GAP: no HP-HT flag exists in wells_drilled.

SELECT
    w.basin_name,
    STRING_AGG(DISTINCT w.terrain_type, ', ') AS terrain,
    COUNT(*) AS exploratory_wells,
    COUNTIF(LOWER(w.result_status) = 'dry_hole') AS dry_holes,
    ROUND(COUNTIF(LOWER(w.result_status) = 'dry_hole') * 100 / COUNT(*), 1) AS dry_hole_rate_pct,
    ROUND(SUM(IF(LOWER(w.result_status) = 'dry_hole', w.drilling_cost_inr_cr, 0)), 0) AS dry_hole_cost_cr,
    ROUND(SUM(w.drilling_cost_inr_cr), 0) AS total_exploratory_cost_cr,
    ROUND(AVG(w.drilling_cost_inr_cr), 1) AS avg_cost_per_well_cr,
    ROUND(AVG(w.actual_depth_meters), 0) AS avg_depth_m
FROM wells_drilled w
WHERE LOWER(w.well_type) = 'exploratory'
  AND w.fiscal_year IN ('FY24', 'FY25', 'FY26')
GROUP BY w.basin_name
ORDER BY avg_cost_per_well_cr DESC;
