-- Answer Key Follow-up SQL: P12__drill_down
-- Question: How many of the 260 E4 executives awaiting E5 promotion consideration fall into Drilling, Production, and F&A?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL counted all historical E4->E5 DPC cases since FY01 (202/206/211 = mostly promoted officers).
-- Semantic audit 2026-10-20: Now the same "due" population as P12 (open 'delayed' E4->E5 cases, Active, still E4), by discipline,
-- Semantic audit 2026-10-20: with the subset lacking a continuous 3-year hard/NE tenure (contiguous Cat-C postings merged).
WITH due AS (
    SELECT d.emp_id
    FROM dpc_cases d
    JOIN employee_master e ON e.emp_id = d.emp_id
    WHERE d.from_grade_id = 'E4' AND d.to_grade_id = 'E5'
      AND LOWER(d.status) = 'delayed' AND d.held_date IS NULL
      AND LOWER(e.employment_status) = 'active' AND e.current_grade_id = 'E4'
),
c_post AS (
    SELECT p.emp_id, p.from_date, COALESCE(p.to_date, DATE '2026-10-19') AS to_date
    FROM posting_history p
    JOIN dim_work_centre w ON w.wc_id = p.wc_id
    WHERE UPPER(w.hard_station_cat) = 'C' AND p.emp_id IN (SELECT emp_id FROM due)
),
flagged AS (
    SELECT *, IF(from_date > DATE_ADD(MAX(to_date) OVER (PARTITION BY emp_id ORDER BY from_date ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), INTERVAL 1 DAY), 1, 0) AS new_run
    FROM c_post
),
runs AS (
    SELECT emp_id, SUM(new_run) OVER (PARTITION BY emp_id ORDER BY from_date) AS run_id, from_date, to_date FROM flagged
),
hs AS (
    SELECT emp_id, MAX(run_days) AS longest_run_days
    FROM (SELECT emp_id, run_id, DATE_DIFF(MAX(to_date), MIN(from_date), DAY) AS run_days FROM runs GROUP BY 1, 2)
    GROUP BY 1
)
SELECT
    dd.name AS discipline,
    dd.name IN ('Drilling', 'Production', 'Finance & Accounts (F&A)') AS asked_discipline,
    COUNT(DISTINCT due.emp_id) AS due_for_e4_e5_review,
    COUNT(DISTINCT IF(hs.emp_id IS NULL, due.emp_id, NULL)) AS never_hard_or_ne_posted,
    COUNT(DISTINCT IF(COALESCE(hs.longest_run_days, 0) < 1095, due.emp_id, NULL)) AS lacking_3yr_hard_ne_tenure
FROM due
JOIN employee_master e ON e.emp_id = due.emp_id
LEFT JOIN dim_discipline dd ON dd.discipline_id = e.discipline_id
LEFT JOIN hs ON hs.emp_id = due.emp_id
GROUP BY dd.name
ORDER BY asked_discipline DESC, due_for_e4_e5_review DESC;
