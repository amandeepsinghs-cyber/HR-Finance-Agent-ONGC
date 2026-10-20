-- Answer Key SQL: H5
-- Question: How many DPC (promotion) cases are pending, and for how long?
-- Type: data
-- Semantic audit 2026-10-20: old SQL used delay_months >= 6 as the 'pending' test and gave no duration. Now: pending = status
-- 'delayed' (DPC not held; same 228 cases), by promotion step, with recorded delay_months (stale extract value) AND months
-- overdue since due_date as of 2026-10-19.
SELECT
    from_grade_id,
    to_grade_id,
    COUNT(DISTINCT emp_id) AS pending_candidates,
    MIN(due_date) AS earliest_due_date,
    ROUND(AVG(delay_months), 1) AS avg_recorded_delay_months,
    MAX(delay_months) AS max_recorded_delay_months,
    ROUND(AVG(DATE_DIFF(DATE '2026-10-19', due_date, MONTH)), 1) AS avg_months_overdue_asof_2026_10_19,
    MAX(DATE_DIFF(DATE '2026-10-19', due_date, MONTH)) AS max_months_overdue_asof_2026_10_19,
    SUM(COUNT(DISTINCT emp_id)) OVER () AS total_pending
FROM dpc_cases
WHERE LOWER(status) = 'delayed' AND held_date IS NULL
GROUP BY from_grade_id, to_grade_id
ORDER BY from_grade_id;
