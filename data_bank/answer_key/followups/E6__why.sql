-- Answer Key Follow-up SQL: E6__why
-- Question: Why are certain advanced technical courses restricted to officers with minimum field experience prerequisites?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL listed 100 programmes across all years (LIMIT 100). Now FY27 prerequisites by category and whether they block this employee.

WITH me AS (
    SELECT current_grade_id AS grade_id, discipline_id, total_tenure_years
    FROM employee_master
    WHERE emp_id = 'EMP-102451'
)
SELECT
    LOWER(t.category) AS category,
    COUNT(*) AS programmes,
    COUNTIF(t.prerequisite_experience_years > 0) AS with_prerequisite,
    MAX(t.prerequisite_experience_years) AS max_prerequisite_years,
    ANY_VALUE(me.total_tenure_years) AS my_experience_years,
    COUNTIF(t.prerequisite_experience_years > me.total_tenure_years) AS blocked_for_me
FROM training_calendar t
CROSS JOIN me
WHERE t.fiscal_year = 'FY27'
GROUP BY category
ORDER BY with_prerequisite DESC, category;
