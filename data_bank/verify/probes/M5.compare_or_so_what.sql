-- Probe ID: M5.compare_or_so_what
-- Parent ID: M5
-- Answer Type: sql
-- Question: How does this week's access refusal rate compare against the 30-day baseline?
-- Personas: CMD
-- Tables: access_audit_log
-- Drill Dims: access_audit_log.date
-- Story IDs: S37
-- Expected Output: table
-- Handcrafted: true

SELECT
    date,
    COUNT(*) AS denial_count
FROM access_audit_log
WHERE access_decision LIKE 'DENIED%'
GROUP BY date
ORDER BY date DESC
LIMIT 14;
