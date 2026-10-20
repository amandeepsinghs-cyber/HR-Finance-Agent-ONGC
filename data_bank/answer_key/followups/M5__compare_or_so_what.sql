-- Answer Key Follow-up SQL: M5__compare_or_so_what
-- Question: How does this week's frequency of access violations compare with the 30-day baseline security audit log?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL listed the last 14 daily counts with no baseline.
-- Semantic audit 2026-10-20: Now: this week's denials (13-19 Oct) vs the preceding 30-day baseline (13 Sep-12 Oct) scaled to a 7-day rate, by classification with an overall total.

WITH d AS (
    SELECT date, resource_data_classification
    FROM access_audit_log
    WHERE LOWER(access_decision) LIKE 'denied%'
      AND date BETWEEN DATE_SUB(DATE '2026-10-19', INTERVAL 36 DAY) AND DATE '2026-10-19'
)
SELECT
    COALESCE(resource_data_classification, 'ALL CONFIDENTIAL') AS classification,
    COUNTIF(date BETWEEN DATE_SUB(DATE '2026-10-19', INTERVAL 6 DAY) AND DATE '2026-10-19') AS denials_this_week,
    COUNTIF(date BETWEEN DATE_SUB(DATE '2026-10-19', INTERVAL 36 DAY) AND DATE_SUB(DATE '2026-10-19', INTERVAL 7 DAY)) AS denials_prior_30d,
    ROUND(COUNTIF(date BETWEEN DATE_SUB(DATE '2026-10-19', INTERVAL 36 DAY) AND DATE_SUB(DATE '2026-10-19', INTERVAL 7 DAY)) * 7.0 / 30, 2) AS baseline_per_week,
    ROUND(SAFE_DIVIDE(COUNTIF(date BETWEEN DATE_SUB(DATE '2026-10-19', INTERVAL 6 DAY) AND DATE '2026-10-19'),
          COUNTIF(date BETWEEN DATE_SUB(DATE '2026-10-19', INTERVAL 36 DAY) AND DATE_SUB(DATE '2026-10-19', INTERVAL 7 DAY)) * 7.0 / 30), 2) AS ratio_vs_baseline
FROM d
GROUP BY ROLLUP(resource_data_classification)
ORDER BY classification = 'ALL CONFIDENTIAL' DESC, denials_this_week DESC;
