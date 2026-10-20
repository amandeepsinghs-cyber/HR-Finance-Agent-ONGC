-- Probe ID: F8.drill_down
-- Parent ID: F8
-- Answer Type: sql
-- Question: What is the 3-year trailing finding cost ($/BOE) in deepwater Western Offshore versus Krishna-Godavari and Assam-Arakan basins?
-- Personas: Director (Finance)
-- Tables: reserves_annual
-- Drill Dims: reserves_annual.basin_name
-- Story IDs: S24
-- Expected Output: table
-- Handcrafted: true

SELECT
    r.basin_name,
    AVG(r.finding_cost_usd_per_boe) AS avg_finding_cost_usd_boe
FROM reserves_annual r
WHERE r.basin_name IN ('Western Offshore', 'Krishna Godavari', 'Assam Arakan')
  AND r.fiscal_year IN ('FY26', '2026')
GROUP BY r.basin_name
ORDER BY r.basin_name;
