-- Answer Key SQL: E6
-- Question: Which training programmes can I take this year?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL listed all 36 FY27 programmes without checking eligibility or whether they are still ahead of 2026-10-19.
-- Semantic audit 2026-10-20: Now filters to the employee's grade and experience prerequisite and flags still_open / discipline_listed.

WITH me AS (
    SELECT current_grade_id AS grade_id, discipline_id, total_tenure_years
    FROM employee_master
    WHERE emp_id = 'EMP-102451'
)
SELECT
    t.programme_id,
    t.programme_name,
    t.institute,
    t.location_city,
    LOWER(t.category) AS category,
    t.start_date,
    t.duration_days,
    t.prerequisite_experience_years,
    t.start_date >= DATE '2026-10-19' AS still_open,
    me.discipline_id IN UNNEST(t.eligible_disciplines) AS discipline_listed
FROM training_calendar t
CROSS JOIN me
WHERE t.fiscal_year = 'FY27'
  AND me.grade_id IN UNNEST(t.eligible_grades)
  AND t.prerequisite_experience_years <= me.total_tenure_years
ORDER BY t.start_date;
