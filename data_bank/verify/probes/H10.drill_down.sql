-- Probe ID: H10.drill_down
-- Parent ID: H10
-- Answer Type: sql
-- Question: Which specific executives meet the criteria for transfer from Delhi/Dehradun to Assam and Tripura assets?
-- Personas: Director (HR)
-- Tables: posting_history, dim_work_centre
-- Drill Dims: dim_work_centre.city
-- Story IDs: S20
-- Expected Output: table
-- Handcrafted: true

WITH numbered_postings AS (
    SELECT
        p.emp_id,
        p.wc_id,
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
        datediff('month', MIN(from_date), DATE '2026-10-19') AS continuous_tenure_months
    FROM numbered_postings
    GROUP BY emp_id, wc_id, island_id
    HAVING BOOL_OR(to_date IS NULL)
)
SELECT
    dim_work_centre.city,
    COUNT(DISTINCT ci.emp_id) AS metric_1
FROM current_islands ci
JOIN dim_work_centre ON ci.wc_id = dim_work_centre.wc_id
WHERE dim_work_centre.city IN ('New Delhi', 'Dehradun') AND ci.continuous_tenure_months >= 36
GROUP BY dim_work_centre.city
ORDER BY dim_work_centre.city
LIMIT 100;
