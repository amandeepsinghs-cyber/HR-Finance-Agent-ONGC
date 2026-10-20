-- Answer Key Follow-up SQL: E2__drill_down
-- Question: How many years of cumulative tenure have I completed at my current work centre and station cluster?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL gave cluster only. Now both current work-centre and cluster cumulative years (JRTP 4.2: sum of all postings), with the 10-year cap.

WITH cur AS (
    SELECT p.wc_id, w.cluster_id
    FROM posting_history p
    JOIN dim_work_centre w ON p.wc_id = w.wc_id
    WHERE p.emp_id = 'EMP-102451' AND p.is_current_posting = TRUE
),
stints AS (
    SELECT p.wc_id, w.cluster_id,
           DATE_DIFF(COALESCE(p.to_date, DATE '2026-10-19'), p.from_date, DAY) / 365.25 AS yrs
    FROM posting_history p
    JOIN dim_work_centre w ON p.wc_id = w.wc_id
    WHERE p.emp_id = 'EMP-102451'
)
SELECT
    cur.wc_id,
    ROUND(SUM(IF(s.wc_id = cur.wc_id, s.yrs, 0)), 1) AS wc_cumulative_years,
    cur.cluster_id,
    ROUND(SUM(IF(s.cluster_id = cur.cluster_id, s.yrs, 0)), 1) AS cluster_cumulative_years,
    10 AS jrtp_cluster_cap_years,
    COUNT(*) AS postings_on_record
FROM stints s CROSS JOIN cur
GROUP BY cur.wc_id, cur.cluster_id;
