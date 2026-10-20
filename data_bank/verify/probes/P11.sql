-- Probe ID: P11
-- Parent ID: None
-- Answer Type: sql_plus_rag
-- Question: Under the transfer policy, who in Delhi has exceeded the cumulative-tenure cap, and who is exempt because they retire soon?
-- Personas: CMD, Director (HR)
-- Tables: posting_history, employee_master, dim_work_centre
-- Drill Dims: posting_history.exemption_tag
-- Story IDs: S1
-- Expected Output: table
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
    cd.exemption_tag,
    cd.grade_id,
    COUNT(DISTINCT CASE WHEN dt.cum_days >= 3652 THEN cd.emp_id END) AS total_cumulative_10yr_breaches,
    COUNT(DISTINCT CASE WHEN dt.cum_days >= 1826 THEN cd.emp_id END) AS continuous_5yr_overstay,
    COUNT(DISTINCT CASE WHEN dt.cum_days >= 3652 AND e.dob <= DATE '1969-10-19' THEN cd.emp_id END) AS superannuation_exempt_3yr
FROM current_delhi cd
JOIN delhi_tenure dt ON cd.emp_id = dt.emp_id
JOIN employee_master e ON cd.emp_id = e.emp_id
GROUP BY cd.exemption_tag, cd.grade_id
ORDER BY cd.exemption_tag, cd.grade_id;
