-- Answer Key SQL: M5
-- Question: CMD: "Who tried to access confidential data this week?"
-- Type: data
-- Semantic audit 2026-10-20: Old SQL had no date window (all 91 days of log) despite 'this week'.
-- Semantic audit 2026-10-20: Now: confidential-resource access attempts in the 7 days to 19-Oct-2026 (13-19 Oct), per user, with denied/allowed split.

SELECT
    a.user_id,
    a.user_role,
    a.user_department,
    a.user_grade,
    a.user_wc_id,
    a.resource_data_classification,
    a.requested_resource,
    COUNT(*) AS attempts,
    COUNTIF(LOWER(a.access_decision) LIKE 'denied%') AS denied_attempts,
    COUNTIF(LOWER(a.access_decision) = 'allowed') AS allowed_attempts,
    MAX(a.date) AS last_attempt_date
FROM access_audit_log a
WHERE a.date BETWEEN DATE_SUB(DATE '2026-10-19', INTERVAL 6 DAY) AND DATE '2026-10-19'
  AND LOWER(a.resource_data_classification) LIKE 'confidential%'
GROUP BY a.user_id, a.user_role, a.user_department, a.user_grade, a.user_wc_id, a.resource_data_classification, a.requested_resource
ORDER BY denied_attempts DESC, last_attempt_date DESC, a.user_id;
