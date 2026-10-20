-- Answer Key Follow-up SQL: M5__why
-- Question: Why did specific user accounts trigger repeated RBAC access denials on confidential commercial and personnel tables?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL counted denial reasons over the whole log and never tested the 'repeated denials' premise.
-- Semantic audit 2026-10-20: Now: denial reasons with this-week and full-log counts, distinct users and the maximum denials by any single account (tests whether any account is a repeat offender).

WITH d AS (
    SELECT * FROM access_audit_log WHERE LOWER(access_decision) LIKE 'denied%'
),
u AS (
    SELECT user_id, COUNT(*) AS user_denials FROM d GROUP BY user_id
)
SELECT
    d.resource_data_classification,
    d.denial_reason,
    COUNTIF(d.date BETWEEN DATE_SUB(DATE '2026-10-19', INTERVAL 6 DAY) AND DATE '2026-10-19') AS denials_this_week,
    COUNT(*) AS denials_full_log,
    COUNT(DISTINCT d.user_id) AS distinct_users,
    MAX(u.user_denials) AS max_denials_by_one_user,
    MIN(d.date) AS log_first_date
FROM d
JOIN u USING (user_id)
GROUP BY d.resource_data_classification, d.denial_reason
ORDER BY denials_this_week DESC, denials_full_log DESC;
