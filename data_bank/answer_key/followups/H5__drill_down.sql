-- Answer Key Follow-up SQL: H5__drill_down
-- Question: Which specific grades (e.g. E4 to E5, E5 to E6) and disciplines have DPC meetings delayed beyond 6 months?
-- Type: data
-- Semantic audit 2026-10-20: pending defined by status 'delayed' (consistent with H5) instead of delay_months>=6 (same rows);
-- added promotion step, recorded delay and months overdue; ordered by size.
SELECT
    CONCAT(d.from_grade_id, '->', d.to_grade_id) AS promotion_step,
    disc.name AS discipline,
    COUNT(DISTINCT d.emp_id) AS pending_candidates,
    ROUND(AVG(d.delay_months), 1) AS avg_recorded_delay_months,
    ROUND(AVG(DATE_DIFF(DATE '2026-10-19', d.due_date, MONTH)), 1) AS avg_months_overdue_asof_2026_10_19
FROM dpc_cases d
JOIN dim_discipline disc ON d.discipline_id = disc.discipline_id
WHERE LOWER(d.status) = 'delayed' AND d.delay_months >= 6
GROUP BY promotion_step, disc.name
ORDER BY pending_candidates DESC, promotion_step, discipline;
