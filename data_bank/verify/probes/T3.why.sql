-- Probe ID: T3.why
-- Parent ID: T3
-- Answer Type: sql_plus_rag
-- Question: What are the primary competency or experience gaps identified for successors?
-- Personas: Director (HR)
-- Tables: succession_plan
-- Drill Dims: succession_plan.readiness_gap_reason
-- Story IDs: S4
-- Expected Output: table
-- Handcrafted: true

SELECT
    COALESCE(sp.readiness_gap_reason, 'No_Gap_Identified') AS readiness_gap_reason,
    COUNT(DISTINCT sp.position_id) AS count
FROM succession_plan sp
GROUP BY COALESCE(sp.readiness_gap_reason, 'No_Gap_Identified')
ORDER BY count DESC;
