-- Probe ID: H5.why
-- Parent ID: H5
-- Answer Type: sql_plus_rag
-- Question: What procedural bottlenecks (e.g. pending vigilance clearances, APAR grading appeals, seniority litigation) delayed convening the DPCs?
-- Personas: Director (HR)
-- Tables: dpc_cases
-- Drill Dims: dpc_cases.delay_bottleneck_reason
-- Story IDs: S11
-- Expected Output: table
-- Handcrafted: true

SELECT
    delay_bottleneck_reason,
    AVG(delay_months) AS avg_delay_months,
    COUNT(*) AS case_count
FROM dpc_cases
WHERE delay_months >= 6
GROUP BY delay_bottleneck_reason
ORDER BY case_count DESC;
