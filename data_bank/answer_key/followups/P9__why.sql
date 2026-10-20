-- Answer Key Follow-up SQL: P9__why
-- Question: Why does the statutory POSH policy mandate time-bound inquiry completion within 90 days?
-- Type: policy
-- Semantic audit 2026-10-20: old query returned 5 arbitrary CDA-rule (P1-01) fragments. GAP: the POSH Act 90-day
-- rule is not in the document corpus; answered with the ICC inquiry-duration record against the 90-day norm.

SELECT
    fiscal_year,
    COUNT(*) AS cases_received,
    COUNTIF(LOWER(status) != 'under_inquiry') AS cases_closed,
    COUNTIF(LOWER(status) != 'under_inquiry' AND inquiry_days <= 90) AS closed_within_90_days,
    ROUND(100 * SAFE_DIVIDE(COUNTIF(LOWER(status) != 'under_inquiry' AND inquiry_days <= 90),
                            COUNTIF(LOWER(status) != 'under_inquiry')), 1) AS pct_closed_within_90,
    ROUND(AVG(IF(LOWER(status) != 'under_inquiry', inquiry_days, NULL)), 1) AS avg_inquiry_days_closed,
    MAX(inquiry_days) AS max_inquiry_days
FROM posh_cases
GROUP BY fiscal_year
ORDER BY fiscal_year;
