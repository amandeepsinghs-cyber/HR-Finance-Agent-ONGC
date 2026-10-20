-- Probe ID: X6
-- Parent ID: None
-- Answer Type: sql
-- Question: What is the progress on our renewable energy investments (Solar, Wind, Green Hydrogen), and what capacity is operational?
-- Personas: CMD
-- Tables: energy_transition
-- Drill Dims: energy_transition.technology_type
-- Story IDs: S34
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 1000.0 (transition_capex_fy26_cr)
-- Expected Range: 900.0 - 1100.0 (tolerance: ±10.0%)

SELECT
    technology_type,
    SUM(installed_capacity_mw) AS total_mw,
    SUM(annual_capex_inr_cr) AS annual_capex_cr
FROM energy_transition
WHERE fiscal_year IN ('FY26', '2026')
GROUP BY technology_type
ORDER BY total_mw DESC;
