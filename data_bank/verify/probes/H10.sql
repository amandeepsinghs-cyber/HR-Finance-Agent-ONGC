-- Probe ID: H10
-- Parent ID: None
-- Answer Type: document_gen
-- Question: Generate an Excel transfer proposal for FY27 using rotation rules.
-- Personas: Director (HR)
-- Tables: posting_history, employee_master, sanctioned_posts, dim_work_centre
-- Drill Dims: dim_work_centre.name
-- Story IDs: S20
-- Expected Output: document
-- Handcrafted: true
-- Story Target: 210.0 (total_agt_proposed_transfers)
-- Expected Range: 189.0 - 231.0 (tolerance: ±10.0%)

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
    dim_work_centre.name,
    COUNT(DISTINCT ci.emp_id) AS metric_1
FROM current_islands ci
JOIN dim_work_centre ON ci.wc_id = dim_work_centre.wc_id
WHERE ci.continuous_tenure_months >= 36
GROUP BY dim_work_centre.name
ORDER BY dim_work_centre.name
LIMIT 100;
