-- Answer Key SQL: C2
-- Question: Who is overdue for transfer under the rotation policy, and which hard or remote stations (NE, offshore) are short of people to receive them?
-- Type: data
-- Semantic audit 2026-10-20: previous SQL only counted in-position executives at four hand-picked NE work
-- centres (WC-ASM/JOR/TRI/SIL) - it identified neither who is overdue nor any shortfall. Now two sections:
--   section 'overdue_pool'      : executives overdue under JRTP Clause 3.2 (>= 60 months continuous stay at the
--                                 current work centre, hrfin_gold.v_continuous_stay) excluding the Clause 7
--                                 3-year pre-retirement protection, by current work centre (top 10 sources);
--   section 'receiving_station' : hard/remote stations (hard_station_cat 'C', NE sector or offshore) with an
--                                 executive vacancy vs FY26 sanctioned posts (sanctioned_posts, E-grades).
-- company_overdue_total repeats the company-wide overdue count on every row for the headline.
-- Semantic audit 2026-10-20 (alignment with C1/H10/X10): overdue pool also excludes executives whose current
-- posting carries a valid exemption_tag ('None' = no tag; exemption_valid_until >= 2026-10-19 or NULL).

WITH overdue AS (
    SELECT v.wc_id, v.emp_id
    FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay` v
    WHERE v.is_current_stay = TRUE
      AND v.grade_id LIKE 'E%'
      AND v.continuous_stay_months >= 60
      AND DATE_DIFF(v.retirement_date, DATE '2026-10-19', DAY) > 3 * 365.25
      AND v.emp_id NOT IN (
          SELECT ph.emp_id FROM posting_history ph
          WHERE ph.is_current_posting = TRUE
            AND NULLIF(ph.exemption_tag, 'None') IS NOT NULL
            AND (ph.exemption_valid_until >= DATE '2026-10-19' OR ph.exemption_valid_until IS NULL)
      )
),
od_wc AS (
    SELECT wc_id, COUNT(DISTINCT emp_id) AS overdue_executives FROM overdue GROUP BY wc_id
),
sp AS (
    SELECT wc_id,
           SUM(sanctioned_strength) AS exec_sanctioned,
           SUM(in_position_strength) AS exec_in_position,
           SUM(vacancy_count) AS exec_vacancy
    FROM sanctioned_posts
    WHERE fiscal_year = 'FY26' AND grade_id LIKE 'E%'
    GROUP BY wc_id
),
tot AS (SELECT COUNT(DISTINCT emp_id) AS company_overdue_total FROM overdue),
pool AS (
    SELECT 'overdue_pool' AS section, w.wc_id, w.short_name, w.hard_station_cat, w.sector, w.onshore_offshore,
           o.overdue_executives, sp.exec_sanctioned, sp.exec_in_position, sp.exec_vacancy
    FROM od_wc o
    JOIN dim_work_centre w ON o.wc_id = w.wc_id
    LEFT JOIN sp ON sp.wc_id = o.wc_id
    ORDER BY o.overdue_executives DESC
    LIMIT 10
),
recv AS (
    SELECT 'receiving_station' AS section, w.wc_id, w.short_name, w.hard_station_cat, w.sector, w.onshore_offshore,
           COALESCE(o.overdue_executives, 0) AS overdue_executives, sp.exec_sanctioned, sp.exec_in_position, sp.exec_vacancy
    FROM sp
    JOIN dim_work_centre w ON sp.wc_id = w.wc_id
    LEFT JOIN od_wc o ON o.wc_id = sp.wc_id
    WHERE (w.hard_station_cat = 'C' OR LOWER(w.sector) = 'ne' OR LOWER(w.onshore_offshore) = 'offshore')
      AND sp.exec_vacancy > 0
)
SELECT u.*, tot.company_overdue_total,
       ROUND(u.exec_vacancy * 100.0 / NULLIF(u.exec_sanctioned, 0), 1) AS exec_vacancy_pct
FROM (SELECT * FROM pool UNION ALL SELECT * FROM recv) u
CROSS JOIN tot
ORDER BY u.section, CASE WHEN u.section = 'overdue_pool' THEN -u.overdue_executives ELSE -u.exec_vacancy END;
