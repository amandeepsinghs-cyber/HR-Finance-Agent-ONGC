-- Answer Key Follow-up SQL: M5__drill_down
-- Question: Break down the unauthorized access attempts by department (HR vs Finance vs Operations) and data type (salary, transfer, P&L).
-- Type: data
-- Semantic audit 2026-10-20: Old SQL had no date window (whole log).
-- Semantic audit 2026-10-20: Now: this week's (13-19 Oct 2026) denied attempts by department x data classification x resource.

SELECT
    user_department,
    resource_data_classification,
    requested_resource,
    COUNT(*) AS denial_count,
    COUNT(DISTINCT user_id) AS distinct_users
FROM access_audit_log
WHERE LOWER(access_decision) LIKE 'denied%'
  AND date BETWEEN DATE_SUB(DATE '2026-10-19', INTERVAL 6 DAY) AND DATE '2026-10-19'
GROUP BY user_department, resource_data_classification, requested_resource
ORDER BY denial_count DESC, user_department, resource_data_classification;
