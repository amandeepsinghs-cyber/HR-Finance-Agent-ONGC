-- Probe ID: T3.compare_or_so_what
-- Parent ID: T3
-- Answer Type: sql
-- Question: How do successors compare on North East hardship posting experience?
-- Personas: Director (HR)
-- Tables: succession_plan
-- Drill Dims: succession_plan.position_id
-- Story IDs: S4
-- Expected Output: table
-- Handcrafted: true

SELECT
    sp.position_id,
    sp.role_title,
    sp.successor_1_has_ne_hard_station,
    sp.successor_2_has_ne_hard_station
FROM succession_plan sp
WHERE sp.criticality_tier = 'Tier_1_Critical'
ORDER BY sp.position_id;
