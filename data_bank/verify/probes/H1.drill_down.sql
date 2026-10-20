-- Probe ID: H1.drill_down
-- Parent ID: H1
-- Answer Type: sql
-- Question: How many of these executives are in non-executive and junior executive grades (E1–E4) versus senior management (E6–E9)?
-- Personas: Director (HR)
-- Tables: posting_history, dim_grade
-- Drill Dims: dim_grade.group
-- Story IDs: S38
-- Expected Output: table
-- Handcrafted: true

WITH numbered_postings AS (
    SELECT
        p.emp_id,
        p.wc_id,
        p.grade_id,
        p.from_date,
        p.to_date,
        ROW_NUMBER() OVER (PARTITION BY p.emp_id ORDER BY p.from_date, p.posting_id) -
        ROW_NUMBER() OVER (PARTITION BY p.emp_id, p.wc_id ORDER BY p.from_date, p.posting_id) AS island_id
    FROM posting_history p
),
current_islands AS (
    SELECT
        emp_id,
        MAX(grade_id) AS current_grade_id,
        datediff('month', MIN(from_date), DATE '2026-10-19') AS continuous_tenure_months
    FROM numbered_postings
    GROUP BY emp_id, wc_id, island_id
    HAVING BOOL_OR(to_date IS NULL)
)
SELECT
    dim_grade.group,
    COUNT(DISTINCT ci.emp_id) AS metric_1
FROM current_islands ci
LEFT JOIN dim_grade ON ci.current_grade_id = dim_grade.grade_id
WHERE ci.continuous_tenure_months > 36
GROUP BY dim_grade.group
ORDER BY dim_grade.group
LIMIT 100;
