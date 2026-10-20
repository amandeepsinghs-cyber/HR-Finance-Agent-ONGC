-- Probe ID: M5.drill_down
-- Parent ID: M5
-- Answer Type: sql
-- Question: Which departments and resource classifications account for the highest volume of access denials?
-- Personas: CMD
-- Tables: access_audit_log
-- Drill Dims: access_audit_log.user_department, access_audit_log.resource_data_classification
-- Story IDs: S37
-- Expected Output: table
-- Handcrafted: true

SELECT
    user_department,
    resource_data_classification,
    COUNT(*) AS denial_count
FROM access_audit_log
WHERE access_decision LIKE 'DENIED%'
GROUP BY user_department, resource_data_classification
ORDER BY denial_count DESC;
