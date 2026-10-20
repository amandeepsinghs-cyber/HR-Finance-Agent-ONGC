-- Probe ID: T2.drill_down
-- Parent ID: T2
-- Answer Type: sql
-- Question: Which of the 412 Delhi-based executives with 5+ years hold technical designations needed in Assam or Tripura?
-- Personas: CMD, Director (HR)
-- Tables: posting_history, employee_master, dim_work_centre, dim_discipline
-- Drill Dims: posting_history.discipline_id
-- Story IDs: S1
-- Expected Output: table
-- Handcrafted: true

WITH current_delhi AS (
    SELECT p.emp_id, p.grade_id, p.discipline_id
    FROM posting_history p
    WHERE p.wc_id = 'WC-DEL' AND p.to_date IS NULL AND p.grade_id LIKE 'E%'
),
delhi_tenure AS (
    SELECT p.emp_id, SUM(datediff('day', p.from_date, COALESCE(p.to_date, DATE '2026-10-19'))) AS cum_days
    FROM posting_history p
    WHERE p.wc_id = 'WC-DEL'
    GROUP BY p.emp_id
)
SELECT
    cd.grade_id,
    cd.discipline_id,
    COUNT(DISTINCT CASE WHEN dt.cum_days >= 3652 THEN cd.emp_id END) AS ten_yr_breaches,
    COUNT(DISTINCT CASE WHEN dt.cum_days >= 1826 THEN cd.emp_id END) AS five_yr_overstay
FROM current_delhi cd
JOIN delhi_tenure dt ON cd.emp_id = dt.emp_id
GROUP BY cd.grade_id, cd.discipline_id
ORDER BY cd.grade_id, cd.discipline_id;
