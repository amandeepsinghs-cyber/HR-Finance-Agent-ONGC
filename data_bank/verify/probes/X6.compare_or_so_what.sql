-- Probe ID: X6.compare_or_so_what
-- Parent ID: X6
-- Answer Type: sql
-- Question: How does our renewable capex allocation compare against the Net-Zero 2038 milestone trajectory?
-- Personas: CMD
-- Tables: energy_transition
-- Drill Dims: energy_transition.technology_type
-- Story IDs: S34
-- Expected Output: table
-- Handcrafted: true

SELECT
    technology_type,
    SUM(cumulative_capex_inr_cr) AS cumulative_capex_cr,
    BOOL_AND(net_zero_2038_roadmap_milestone_met) AS all_milestones_met
FROM energy_transition
WHERE fiscal_year IN ('FY26', '2026')
GROUP BY technology_type
ORDER BY cumulative_capex_cr DESC;
