-- Probe ID: H1.why
-- Parent ID: H1
-- Answer Type: sql_plus_rag
-- Question: What operational dependencies or retention justifications have kept these officers beyond their 3-year tenure?
-- Personas: Director (HR)
-- Tables: posting_history
-- Drill Dims: posting_history.exemption_reason_code
-- Story IDs: S38
-- Expected Output: table
-- Handcrafted: true

WITH numbered_postings AS (
    SELECT
        p.emp_id,
        p.wc_id,
        p.exemption_reason_code,
        p.exemption_tag,
        p.from_date,
        p.to_date,
        ROW_NUMBER() OVER (PARTITION BY p.emp_id ORDER BY p.from_date, p.posting_id) -
        ROW_NUMBER() OVER (PARTITION BY p.emp_id, p.wc_id ORDER BY p.from_date, p.posting_id) AS island_id
    FROM posting_history p
),
current_islands AS (
    SELECT
        emp_id,
        MAX(exemption_reason_code) AS exemption_reason_code,
        MAX(exemption_tag) AS exemption_tag,
        datediff('month', MIN(from_date), DATE '2026-10-19') AS continuous_tenure_months
    FROM numbered_postings
    GROUP BY emp_id, wc_id, island_id
    HAVING BOOL_OR(to_date IS NULL)
)
SELECT
    ci.exemption_reason_code,
    COUNT(DISTINCT ci.emp_id) AS metric_1
FROM current_islands ci
WHERE ci.continuous_tenure_months > 36 AND ci.exemption_tag IS NOT NULL
GROUP BY ci.exemption_reason_code
ORDER BY ci.exemption_reason_code
LIMIT 100;
