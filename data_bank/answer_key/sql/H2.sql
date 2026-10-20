-- Answer Key SQL: H2
-- Question: Which employees have never served in a hard or remote station?
-- Type: data
-- Semantic audit 2026-10-20: old SQL counted executives CURRENTLY posted in 4 NE work centres (the opposite population).
-- Now: active employees with no posting ever in a Category C (hard/remote) work centre, by grade, with share of grade.
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
    cadre,
    current_grade_id AS grade_id,
    COUNTIF(never_hard) AS never_served_hard_station,
    COUNT(*) AS active_employees,
    ROUND(COUNTIF(never_hard) * 100.0 / COUNT(*), 1) AS pct_of_grade,
    SUM(COUNTIF(never_hard)) OVER () AS company_never_hard,
    SUM(COUNT(*)) OVER () AS company_active,
    SUM(COUNTIF(never_hard AND LOWER(cadre) = 'executive')) OVER () AS executives_never_hard
FROM active
GROUP BY cadre, current_grade_id, level_order
ORDER BY level_order;
