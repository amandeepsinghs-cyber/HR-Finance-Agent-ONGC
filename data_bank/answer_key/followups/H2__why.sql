-- Answer Key Follow-up SQL: H2__why
-- Question: Why have these executives been repeatedly posted across non-hard clusters (e.g. Delhi, Dehradun, Ahmedabad, Mumbai)?
-- Type: data
-- Semantic audit 2026-10-20: old SQL counted postings in NE (hard) clusters - the opposite of the question. Now: for active
-- executives who never served a Category C station, where their posting histories were spent (by cluster), share of the group
-- that has served in each cluster, and their discipline-function mix (JRTP 6.1 mandates hard tenure for technical/operational).
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
, grp AS (
    SELECT a.emp_id, d.function
    FROM active a
    LEFT JOIN dim_discipline d ON d.discipline_id = a.discipline_id
    WHERE a.never_hard AND LOWER(a.cadre) = 'executive'
)
SELECT
    w.cluster_name,
    COUNT(DISTINCT p.emp_id) AS never_hard_execs_served,
    COUNT(*) AS postings,
    ROUND(COUNT(DISTINCT p.emp_id) * 100.0 / (SELECT COUNT(*) FROM grp), 1) AS pct_of_never_hard_execs,
    COUNT(DISTINCT IF(p.is_current_posting, p.emp_id, NULL)) AS currently_posted,
    (SELECT COUNT(*) FROM grp) AS never_hard_execs_total,
    (SELECT COUNTIF(LOWER(function) = 'technical') FROM grp) AS never_hard_technical
FROM posting_history p
JOIN grp ON grp.emp_id = p.emp_id
JOIN dim_work_centre w ON w.wc_id = p.wc_id
GROUP BY w.cluster_name
ORDER BY never_hard_execs_served DESC;
