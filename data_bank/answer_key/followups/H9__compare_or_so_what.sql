-- Answer Key Follow-up SQL: H9__compare_or_so_what
-- Question: What is the average disposal time of internal employee grievances compared to the statutory 60-day charter target?
-- Type: data
-- Semantic audit 2026-10-20: old SQL averaged age_days over ALL case types and statuses (closed cases' age = days since filing,
-- not disposal time). The table has no disposal date, so average disposal time cannot be computed (GAP). Closest honest view:
-- internal grievances (case_type grievance_internal) split open vs closed, with age since filing and count beyond the 60-day
-- charter, as of 2026-10-19 (future-dated filings excluded from ages).
SELECT
    IF(LOWER(status) IN ('pending', 'stayed'), 'open', 'closed') AS status_group,
    COUNT(*) AS grievances,
    ROUND(AVG(IF(DATE_DIFF(DATE '2026-10-19', filing_date, DAY) >= 0, DATE_DIFF(DATE '2026-10-19', filing_date, DAY), NULL)), 0) AS avg_days_since_filing,
    COUNTIF(DATE_DIFF(DATE '2026-10-19', filing_date, DAY) > 60) AS older_than_60_days,
    COUNTIF(DATE_DIFF(DATE '2026-10-19', filing_date, DAY) < 0) AS future_dated_filings,
    60 AS charter_target_days
FROM grievances_litigation
WHERE LOWER(case_type) = 'grievance_internal'
GROUP BY status_group
ORDER BY status_group DESC;
