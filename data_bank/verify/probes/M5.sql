-- Probe ID: M5
-- Parent ID: None
-- Answer Type: sql
-- Question: CMD: "Who tried to access confidential data this week?"
-- Personas: CMD
-- Tables: access_audit_log
-- Drill Dims: access_audit_log.user_id
-- Story IDs: S37
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 14.0 (total_unauthorized_attempts_logged)
-- Expected Range: 12.6 - 15.4 (tolerance: ±10.0%)

SELECT
    user_id,
    requested_resource,
    access_decision,
    COUNT(*) AS attempt_count
FROM access_audit_log
WHERE access_decision LIKE 'DENIED%'
GROUP BY user_id, requested_resource, access_decision
ORDER BY attempt_count DESC;
