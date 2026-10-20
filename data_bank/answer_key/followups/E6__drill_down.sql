-- Answer Key Follow-up SQL: E6__drill_down
-- Question: What upcoming courses are scheduled at ONGC Academy Dehradun and IOGPT Navi Mumbai for my grade and discipline?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL listed every year FY22-FY27 (72 rows, duplicate column), not upcoming courses for the employee's grade.
-- Semantic audit 2026-10-20: Now FY27, grade/prerequisite-eligible, at the two institutes, with still_open and discipline_listed flags.

WITH me AS (
    SELECT current_grade_id AS grade_id, discipline_id, total_tenure_years
    FROM employee_master
    WHERE emp_id = 'EMP-102451'
)
SELECT
    t.programme_name,
    t.institute,
    t.location_city,
    t.start_date,
    t.start_date >= DATE '2026-10-19' AS still_open,
    me.discipline_id IN UNNEST(t.eligible_disciplines) AS discipline_listed
FROM training_calendar t
CROSS JOIN me
WHERE t.fiscal_year = 'FY27'
  AND t.institute IN ('ONGC_Academy_Dehradun', 'IOGPT_Navi_Mumbai')
  AND me.grade_id IN UNNEST(t.eligible_grades)
  AND t.prerequisite_experience_years <= me.total_tenure_years
ORDER BY t.start_date;
