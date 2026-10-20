-- Answer Key SQL: P12
-- Question: Which executives are due for an E4→E5 merit review and have **not** done a North-East or hard posting?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL counted every E4->E5 DPC case since FY01 (mostly completed = already promoted) per
-- Semantic audit 2026-10-20: discipline. "Due" now = open (status 'delayed', not yet held) E4->E5 cases of Active executives
-- Semantic audit 2026-10-20: still in grade E4. Hard/NE = dim_work_centre.hard_station_cat 'C' (Assam, Jorhat, Tripura,
-- Semantic audit 2026-10-20: Bokaro, Rajasthan, Mumbai High/Bassein/Neelam offshore, Eastern Offshore). JRTP Clause 6.1
-- Semantic audit 2026-10-20: requires one continuous 3-year Cat-C tenure: contiguous Cat-C postings are merged (gaps-and-islands).
-- Semantic audit 2026-10-20: Lists every due executive who has NOT completed a continuous 3-year hard/NE tenure.
WITH due AS (
    SELECT d.emp_id, d.fiscal_year AS dpc_fiscal_year, d.due_date, d.pending_reason
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
    SELECT emp_id, MAX(run_days) AS longest_run_days, SUM(run_days) AS total_c_days
    FROM (SELECT emp_id, run_id, DATE_DIFF(MAX(to_date), MIN(from_date), DAY) AS run_days FROM runs GROUP BY 1, 2)
    GROUP BY 1
)
SELECT
    e.emp_id,
    e.name,
    dd.name AS discipline,
    w.short_name AS current_work_centre,
    due.dpc_fiscal_year,
    due.pending_reason,
    hs.emp_id IS NULL AS never_hard_or_ne_posted,
    ROUND(COALESCE(hs.total_c_days, 0) / 365.25, 2) AS hard_ne_service_years,
    ROUND(COALESCE(hs.longest_run_days, 0) / 365.25, 2) AS longest_continuous_hard_ne_years,
    COALESCE(hs.longest_run_days, 0) AS longest_continuous_hard_ne_days
FROM due
JOIN employee_master e ON e.emp_id = due.emp_id
LEFT JOIN dim_discipline dd ON dd.discipline_id = e.discipline_id
LEFT JOIN dim_work_centre w ON w.wc_id = e.current_wc_id
LEFT JOIN hs ON hs.emp_id = due.emp_id
WHERE COALESCE(hs.longest_run_days, 0) < 1095
ORDER BY never_hard_or_ne_posted DESC, longest_continuous_hard_ne_days, e.emp_id;
