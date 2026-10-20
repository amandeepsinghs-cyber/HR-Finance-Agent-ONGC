-- Probe ID: C1
-- Parent ID: None
-- Answer Type: sql
-- Question: How many executives have been posted in the Delhi office for 5 years or more? Break down by grade and discipline.
-- Personas: CMD
-- Tables: posting_history, employee_master, dim_work_centre, dim_grade, dim_discipline
-- Drill Dims: posting_history.grade_id, posting_history.discipline_id
-- Story IDs: S1
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 412.0 (delhi_executives_ge_5yr)
-- Expected Range: 370.8 - 453.2 (tolerance: ±10.0%)

WITH numbered_postings AS (
    SELECT
        p.emp_id,
        p.wc_id,
        p.grade_id,
        p.discipline_id,
        p.from_date,
        p.to_date,
        ROW_NUMBER() OVER (PARTITION BY p.emp_id ORDER BY p.from_date) -
        ROW_NUMBER() OVER (PARTITION BY p.emp_id, p.wc_id ORDER BY p.from_date) AS island_id
    FROM posting_history p
),
islands AS (
    SELECT
        emp_id,
        wc_id,
        island_id,
        MIN(from_date) AS continuous_from_date,
        MAX(COALESCE(to_date, DATE '2026-10-19')) AS continuous_to_date,
        BOOL_OR(to_date IS NULL) AS is_current_stay,
        MAX(grade_id) AS current_grade_id,
        MAX(discipline_id) AS current_discipline_id
    FROM numbered_postings
    GROUP BY emp_id, wc_id, island_id
)
SELECT
    current_grade_id AS grade_id,
    current_discipline_id AS discipline_id,
    COUNT(DISTINCT emp_id) AS delhi_executives_ge_5yr
FROM islands
WHERE is_current_stay = TRUE
  AND wc_id = 'WC-DEL'
  AND current_grade_id LIKE 'E%'
  AND datediff('month', continuous_from_date, DATE '2026-10-19') >= 60
GROUP BY current_grade_id, current_discipline_id
ORDER BY current_grade_id, current_discipline_id;
