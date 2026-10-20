-- Answer Key Follow-up SQL: H2__drill_down
-- Question: Filter the list for E4–E5 executives who are currently within the zone of consideration for promotion to E5/E6.
-- Type: data
-- Semantic audit 2026-10-20: old SQL counted DPC rows for anyone currently in NE work centres (wrong population, no zone test).
-- Now: never-hard-station active E4/E5 executives; zone of consideration = years in current grade >= dim_grade
-- typical_residency_years; plus those with a pending (delayed) DPC case. JRTP 6.2 bars E4s without Cat-C tenure from E4->E5.
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
, grade_entry AS (
    SELECT p.emp_id, MIN(p.from_date) AS grade_from_date
    FROM posting_history p
    JOIN active a ON a.emp_id = p.emp_id AND p.grade_id = a.current_grade_id
    GROUP BY p.emp_id
),
pending_dpc AS (
    SELECT DISTINCT emp_id FROM dpc_cases WHERE LOWER(status) = 'delayed'
)
SELECT
    a.current_grade_id AS grade_id,
    CASE a.current_grade_id WHEN 'E4' THEN 'E5' ELSE 'E6' END AS promotion_to,
    COUNT(*) AS never_hard_executives,
    COUNTIF(DATE_DIFF(DATE '2026-10-19', ge.grade_from_date, MONTH) >= a.typical_residency_years * 12) AS in_zone_of_consideration,
    COUNTIF(pd.emp_id IS NOT NULL) AS with_pending_dpc,
    ROUND(AVG(DATE_DIFF(DATE '2026-10-19', ge.grade_from_date, MONTH)) / 12, 1) AS avg_years_in_grade,
    MAX(a.typical_residency_years) AS residency_norm_years
FROM active a
LEFT JOIN grade_entry ge ON ge.emp_id = a.emp_id
LEFT JOIN pending_dpc pd ON pd.emp_id = a.emp_id
WHERE a.never_hard AND a.current_grade_id IN ('E4', 'E5')
GROUP BY a.current_grade_id
ORDER BY a.current_grade_id;
