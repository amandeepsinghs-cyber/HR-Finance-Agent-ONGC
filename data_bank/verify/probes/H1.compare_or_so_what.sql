-- Probe ID: H1.compare_or_so_what
-- Parent ID: H1
-- Answer Type: sql
-- Question: How does the tenure compliance rate in Corporate HQ Delhi compare with field assets like Ankleshwar and Cambay?
-- Personas: Director (HR)
-- Tables: posting_history, dim_work_centre
-- Drill Dims: dim_work_centre.short_name
-- Story IDs: S38
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
    dim_work_centre.short_name,
    COUNT(DISTINCT CASE WHEN ci.continuous_tenure_months <= 36 THEN ci.emp_id END) * 100.0 / COUNT(DISTINCT ci.emp_id) AS metric_1
FROM current_islands ci
JOIN dim_work_centre ON ci.wc_id = dim_work_centre.wc_id
WHERE dim_work_centre.short_name IN ('Delhi HQ', 'Ankleshwar Asset', 'Cambay Asset')
GROUP BY dim_work_centre.short_name
ORDER BY dim_work_centre.short_name
LIMIT 100;
