-- Answer Key Follow-up SQL: X8__compare_or_so_what
-- Question: What is our current RTI compliance and disposal rate compared to the statutory 30-day timeline mandated by the RTI Act?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL divided on-time disposals by ALL applications incl. 82 still pending (some received <30 days
-- ago), mixing disposal and compliance. Now per FY: disposal rate, % of disposals within 30 days (from dates), and
-- pending applications already past the 30-day limit as of 2026-10-19.
SELECT
    fiscal_year,
    COUNT(*) AS applications,
    COUNTIF(disposed_date IS NOT NULL) AS disposed,
    ROUND(COUNTIF(disposed_date IS NOT NULL) * 100 / COUNT(*), 1) AS disposal_rate_pct,
    COUNTIF(disposed_date IS NOT NULL AND DATE_DIFF(disposed_date, received_date, DAY) <= 30) AS disposed_within_30_days,
    ROUND(COUNTIF(disposed_date IS NOT NULL AND DATE_DIFF(disposed_date, received_date, DAY) <= 30) * 100
          / NULLIF(COUNTIF(disposed_date IS NOT NULL), 0), 1) AS pct_disposals_within_30_days,
    ROUND(AVG(IF(disposed_date IS NOT NULL, DATE_DIFF(disposed_date, received_date, DAY), NULL)), 1) AS avg_days_to_dispose,
    COUNTIF(disposed_date IS NULL AND DATE_DIFF(DATE '2026-10-19', received_date, DAY) > 30) AS pending_beyond_30_days
FROM rti_applications
GROUP BY fiscal_year
ORDER BY fiscal_year;
