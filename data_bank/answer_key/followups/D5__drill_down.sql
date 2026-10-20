-- Answer Key Follow-up SQL: D5__drill_down
-- Question: What is the aggregate number of employees currently stationed at Delhi Corporate HQ?
-- Type: refusal
-- Semantic audit 2026-10-20: Old SQL summed headcount_snapshot over 12 FY26 months for city 'New Delhi' -> 11,421 (12x the stock).
-- Semantic audit 2026-10-20: Now: active employees currently posted at the Delhi Corporate HQ work centre (employee_master), with the Sep-2026 snapshot as cross-check.

SELECT
    w.wc_id,
    w.name AS work_centre,
    COUNT(*) AS active_employees,
    COUNTIF(e.current_grade_id LIKE 'E%') AS executives,
    COUNTIF(e.current_grade_id NOT LIKE 'E%') AS non_executives,
    (SELECT SUM(h.headcount) FROM headcount_snapshot h WHERE h.wc_id = w.wc_id AND h.month = '2026-09') AS snapshot_headcount_2026_09
FROM employee_master e
JOIN dim_work_centre w ON e.current_wc_id = w.wc_id
WHERE LOWER(e.employment_status) = 'active'
  AND w.is_corporate_hq = TRUE
  AND LOWER(w.city) = 'new delhi'
GROUP BY w.wc_id, w.name;
