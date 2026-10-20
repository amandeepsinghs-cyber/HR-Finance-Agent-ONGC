-- Answer Key Follow-up SQL: H5__compare_or_so_what
-- Question: How many eligible executives have completed the required residency period but are still awaiting promotion notification?
-- Type: data
-- Semantic audit 2026-10-20: old SQL returned average delay by grade - it did not count executives who completed residency.
-- Now: for the pending (delayed) DPC candidates, how many have completed the dim_grade typical residency in their current grade
-- (years since first posting in that grade, as of 2026-10-19), by promotion step.
WITH pending AS (
    SELECT DISTINCT d.emp_id, d.from_grade_id, d.to_grade_id
    FROM dpc_cases d
    WHERE LOWER(d.status) = 'delayed'
),
grade_entry AS (
    SELECT p.emp_id, MIN(p.from_date) AS grade_from_date
    FROM posting_history p
    JOIN pending pe ON pe.emp_id = p.emp_id AND p.grade_id = pe.from_grade_id
    GROUP BY p.emp_id
)
SELECT
    CONCAT(pe.from_grade_id, '->', pe.to_grade_id) AS promotion_step,
    COUNT(*) AS pending_candidates,
    MAX(g.typical_residency_years) AS residency_norm_years,
    COUNTIF(DATE_DIFF(DATE '2026-10-19', ge.grade_from_date, MONTH) >= g.typical_residency_years * 12) AS residency_completed_awaiting,
    ROUND(COUNTIF(DATE_DIFF(DATE '2026-10-19', ge.grade_from_date, MONTH) >= g.typical_residency_years * 12) * 100.0 / COUNT(*), 1) AS pct_residency_completed,
    ROUND(AVG(DATE_DIFF(DATE '2026-10-19', ge.grade_from_date, MONTH)) / 12, 1) AS avg_years_in_grade
FROM pending pe
JOIN dim_grade g ON g.grade_id = pe.from_grade_id
LEFT JOIN grade_entry ge ON ge.emp_id = pe.emp_id
GROUP BY promotion_step
ORDER BY promotion_step;
