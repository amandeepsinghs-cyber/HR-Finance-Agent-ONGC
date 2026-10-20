-- Probe ID: T2
-- Parent ID: None
-- Answer Type: document_gen
-- Question: "Who in Delhi has 5+ years?" → "Which of them breach the transfer policy?" → "Match them to vacancies at hard stations." → "Export as an Excel transfer proposal."
-- Personas: CMD, Director (HR)
-- Tables: posting_history, sanctioned_posts, employee_master, dim_work_centre
-- Drill Dims: posting_history.emp_id
-- Story IDs: S1
-- Expected Output: document
-- Handcrafted: true
-- Story Target: 412.0 (delhi_executives_ge_5yr)
-- Expected Range: 370.8 - 453.2 (tolerance: ±10.0%)

WITH current_delhi AS (
    SELECT p.emp_id, p.grade_id, p.discipline_id, COALESCE(p.exemption_tag, 'Impending_Retirement') AS exemption_tag
    FROM posting_history p
    WHERE p.wc_id = 'WC-DEL' AND p.to_date IS NULL AND p.grade_id LIKE 'E%'
),
delhi_tenure AS (
    SELECT
        p.emp_id,
        SUM(datediff('day', p.from_date, COALESCE(p.to_date, DATE '2026-10-19'))) AS cum_days
    FROM posting_history p
    WHERE p.wc_id = 'WC-DEL'
    GROUP BY p.emp_id
)
SELECT
    cd.emp_id,
    cd.grade_id,
    cd.discipline_id,
    cd.exemption_tag,
    ROUND(dt.cum_days / 365.25, 1) AS delhi_years
FROM current_delhi cd
JOIN delhi_tenure dt ON cd.emp_id = dt.emp_id
WHERE dt.cum_days >= 1826
ORDER BY delhi_years DESC
LIMIT 100;
