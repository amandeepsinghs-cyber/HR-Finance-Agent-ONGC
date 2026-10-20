-- Probe ID: T3.drill_down
-- Parent ID: T3
-- Answer Type: sql
-- Question: How many positions have no ready successor (successor 1 readiness not Ready Now)?
-- Personas: Director (HR)
-- Tables: succession_plan
-- Drill Dims: succession_plan.role_title
-- Story IDs: S4
-- Expected Output: table
-- Handcrafted: true

SELECT
    sp.role_title,
    sp.successor_1_readiness,
    COUNT(DISTINCT sp.position_id) AS positions_count
FROM succession_plan sp
GROUP BY sp.role_title, sp.successor_1_readiness
ORDER BY positions_count DESC;
