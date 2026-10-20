-- Answer Key Follow-up SQL: E6__compare_or_so_what
-- Question: How do the mandatory technical training credits compare against managerial and leadership module requirements?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL summed duration over all six FYs. Now FY27 only, technical vs managerial/leadership vs other. No 'mandatory credit' field exists (GAP) - days/programmes are the proxy.

SELECT
    CASE
        WHEN LOWER(category) = 'technical' THEN 'technical'
        WHEN LOWER(category) IN ('leadership', 'general_management') THEN 'managerial_leadership'
        ELSE 'other (hse/finance/renewables)'
    END AS track,
    COUNT(*) AS programmes,
    SUM(duration_days) AS total_days,
    ROUND(AVG(duration_days), 1) AS avg_days_per_programme,
    SUM(seats_capacity) AS seats
FROM training_calendar
WHERE fiscal_year = 'FY27'
GROUP BY track
ORDER BY track DESC;
