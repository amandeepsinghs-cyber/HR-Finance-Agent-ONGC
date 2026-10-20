-- Probe ID: D2.compare_or_so_what
-- Parent ID: D2
-- Answer Type: sql
-- Question: How many executives in Mumbai have completed their standard 3-year tenure and are due for rotation?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: posting_history, dim_work_centre
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: number
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
        wc_id,
        MIN(from_date) AS stay_start_date,
        datediff('month', MIN(from_date), DATE '2026-10-19') AS continuous_tenure_months,
        MAX(grade_id) AS current_grade_id
    FROM numbered_postings
    GROUP BY emp_id, wc_id, island_id
    HAVING BOOL_OR(to_date IS NULL)
)
SELECT
    COUNT(DISTINCT ci.emp_id) AS metric_1
FROM current_islands ci
JOIN dim_work_centre ON ci.wc_id = dim_work_centre.wc_id
WHERE dim_work_centre.city = 'Mumbai'
  AND ci.current_grade_id LIKE 'E%'
  AND ci.continuous_tenure_months >= 36;
