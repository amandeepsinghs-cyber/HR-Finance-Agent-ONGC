-- Probe ID: C1.compare_or_so_what
-- Parent ID: C1
-- Answer Type: sql
-- Question: How does the Delhi retention rate compare with corporate headquarters in Dehradun (Tel Bhavan) and Mumbai?
-- Personas: CMD
-- Tables: posting_history, dim_work_centre
-- Drill Dims: dim_work_centre.city
-- Story IDs: S1
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
        MIN(from_date) AS continuous_from_date,
        datediff('month', MIN(from_date), DATE '2026-10-19') AS continuous_tenure_months
    FROM numbered_postings
    GROUP BY emp_id, wc_id, island_id
    HAVING BOOL_OR(to_date IS NULL)
)
SELECT
    dim_work_centre.city,
    COUNT(DISTINCT CASE WHEN ci.continuous_tenure_months >= 60 THEN ci.emp_id END) * 100.0 / COUNT(DISTINCT ci.emp_id) AS metric_1
FROM current_islands ci
JOIN dim_work_centre ON ci.wc_id = dim_work_centre.wc_id
WHERE dim_work_centre.city IN ('New Delhi', 'Dehradun', 'Mumbai')
GROUP BY dim_work_centre.city
ORDER BY dim_work_centre.city
LIMIT 100;
