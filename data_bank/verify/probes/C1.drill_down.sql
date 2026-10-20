-- Probe ID: C1.drill_down
-- Parent ID: C1
-- Answer Type: sql
-- Question: Which specific disciplines in Delhi (e.g. F&A, HR, MM, Legal) have the highest concentration of E5–E7 officers past 5 years?
-- Personas: CMD
-- Tables: posting_history, dim_work_centre, dim_grade, dim_discipline
-- Drill Dims: posting_history.discipline_id, posting_history.grade_id
-- Story IDs: S1
-- Expected Output: table
-- Handcrafted: true

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
        BOOL_OR(to_date IS NULL) AS is_current_stay,
        MAX(grade_id) AS current_grade_id,
        MAX(discipline_id) AS current_discipline_id
    FROM numbered_postings
    GROUP BY emp_id, wc_id, island_id
)
SELECT
    current_grade_id AS grade_id,
    current_discipline_id AS discipline_id,
    COUNT(DISTINCT emp_id) AS executive_count
FROM islands
WHERE is_current_stay = TRUE
  AND wc_id = 'WC-DEL'
  AND current_grade_id LIKE 'E%'
  AND datediff('month', continuous_from_date, DATE '2026-10-19') >= 60
GROUP BY current_grade_id, current_discipline_id
ORDER BY current_grade_id, current_discipline_id;
