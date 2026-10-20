-- Probe ID: C10.why
-- Parent ID: C10
-- Answer Type: sql_plus_rag
-- Question: Why was gas production below the MoU target in H1 FY26?
-- Personas: CMD
-- Tables: mou_targets
-- Drill Dims: mou_targets.parameter_name
-- Story IDs: S10
-- Expected Output: table
-- Handcrafted: true

SELECT
    parameter_name,
    excellent_target,
    actual_achievement,
    notes_and_exceptions
FROM mou_targets
WHERE parameter_name LIKE '%Gas%'
ORDER BY fiscal_year DESC;
