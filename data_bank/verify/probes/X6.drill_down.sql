-- Probe ID: X6.drill_down
-- Parent ID: X6
-- Answer Type: sql
-- Question: Break down the renewable capacity pipeline (Solar, Wind, Hybrid) across operational and under-construction projects.
-- Personas: CMD
-- Tables: energy_transition
-- Drill Dims: energy_transition.technology_type
-- Story IDs: S34
-- Expected Output: table
-- Handcrafted: true

SELECT
    technology_type,
    SUM(installed_capacity_mw) AS total_mw,
    SUM(annual_capex_inr_cr) AS annual_capex_cr
FROM energy_transition
WHERE fiscal_year IN ('FY26', '2026')
GROUP BY technology_type
ORDER BY total_mw DESC;
