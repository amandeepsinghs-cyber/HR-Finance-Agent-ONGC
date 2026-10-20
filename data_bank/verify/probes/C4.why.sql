-- Probe ID: C4.why
-- Parent ID: C4
-- Answer Type: sql_plus_rag
-- Question: Why are certain critical E7+ positions identified as having zero 'Ready Now' successors in the latest succession board review?
-- Personas: CMD
-- Tables: succession_plan, apar_ratings, promotion_history
-- Drill Dims: succession_plan.role_title
-- Story IDs: S4
-- Expected Output: table
-- Handcrafted: true

SELECT
    sp.role_title,
    sp.successor_1_readiness,
    COUNT(DISTINCT sp.position_id) AS position_count
FROM succession_plan sp
WHERE sp.successor_1_readiness IN ('Ready_1_to_2_years', 'Ready_3_to_5_years')
GROUP BY sp.role_title, sp.successor_1_readiness
ORDER BY position_count DESC;
