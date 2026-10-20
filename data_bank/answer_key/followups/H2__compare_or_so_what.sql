-- Answer Key Follow-up SQL: H2__compare_or_so_what
-- Question: How does the percentage of hard-station unserved officers in HR and Finance compare with Drilling and Production disciplines?
-- Type: data
-- Semantic audit 2026-10-20: old SQL counted executives currently in 4 NE WCs by discipline (no percentage, wrong population).
-- Now: % of active executives who never served a Category C station, for HR, F&A, Drilling, Production and all executives.
WITH ever_hard AS (
    -- 'hard or remote station' = Category C work centre (JRTP 2.0/6.1: NE, offshore, Bokaro CBM, Rajasthan)
    SELECT p.emp_id, LOGICAL_OR(LOWER(w.hard_station_cat) = 'c') AS served_cat_c
    FROM posting_history p
    JOIN dim_work_centre w ON w.wc_id = p.wc_id
    GROUP BY p.emp_id
),
active AS (
    SELECT e.*, g.cadre, g.level_order, g.typical_residency_years,
           NOT IFNULL(h.served_cat_c, FALSE) AS never_hard
    FROM employee_master e
    JOIN dim_grade g ON g.grade_id = e.current_grade_id
    LEFT JOIN ever_hard h ON h.emp_id = e.emp_id
    WHERE LOWER(e.employment_status) = 'active'
)
SELECT
    d.name AS discipline,
    d.function,
    COUNT(*) AS active_executives,
    COUNTIF(a.never_hard) AS never_hard,
    ROUND(COUNTIF(a.never_hard) * 100.0 / COUNT(*), 1) AS pct_never_hard
FROM active a
JOIN dim_discipline d ON d.discipline_id = a.discipline_id
WHERE LOWER(a.cadre) = 'executive'
  AND d.name IN ('Human Resources (HR)', 'Finance & Accounts (F&A)', 'Drilling', 'Production')
GROUP BY d.name, d.function
UNION ALL
SELECT 'All executives', 'all', COUNT(*), COUNTIF(never_hard), ROUND(COUNTIF(never_hard) * 100.0 / COUNT(*), 1)
FROM active
WHERE LOWER(cadre) = 'executive'
ORDER BY pct_never_hard DESC;
