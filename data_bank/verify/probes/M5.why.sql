-- Probe ID: M5.why
-- Parent ID: M5
-- Answer Type: sql
-- Question: What are the primary reasons recorded for access authorization denials?
-- Personas: CMD
-- Tables: access_audit_log
-- Drill Dims: access_audit_log.denial_reason
-- Story IDs: S37
-- Expected Output: table
-- Handcrafted: true

SELECT
    COALESCE(denial_reason, 'Access_Denied_Policy') AS denial_reason,
    COUNT(*) AS denial_count
FROM access_audit_log
WHERE access_decision LIKE 'DENIED%'
GROUP BY denial_reason
ORDER BY denial_count DESC;
