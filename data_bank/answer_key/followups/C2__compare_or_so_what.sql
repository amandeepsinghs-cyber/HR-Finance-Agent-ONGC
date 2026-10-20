-- Answer Key Follow-up SQL: C2__compare_or_so_what
-- Question: How many of the overdue executives have never completed a mandatory tenure in a Category-C or offshore location?
-- Type: data
-- Semantic audit 2026-10-20: previous SQL used all E3-E5 employees (not the overdue population), counted
-- separated staff ("OR separation_date IS NULL") and treated ANY posting in a C/offshore centre as a completed
-- tenure. Now: the parent's overdue population (>= 60 months continuous stay, outside the 3-year
-- pre-retirement protection), and "completed mandatory tenure" = a posting of >= 36 months (JRTP Clause 6.1)
-- in a Category-C or offshore work centre.
-- Semantic audit 2026-10-20 (alignment with C1/H10/X10): overdue pool also excludes executives whose current
-- posting carries a valid exemption_tag ('None' = no tag; exemption_valid_until >= 2026-10-19 or NULL).

WITH overdue AS (
    SELECT DISTINCT v.emp_id
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
hist AS (
    SELECT p.emp_id,
           MAX(IF(w.hard_station_cat = 'C' AND p.tenure_months >= 36, 1, 0)) AS cat_c_36m,
           MAX(IF(LOWER(w.onshore_offshore) = 'offshore' AND p.tenure_months >= 36, 1, 0)) AS offshore_36m,
           MAX(IF(w.hard_station_cat = 'C' OR LOWER(w.onshore_offshore) = 'offshore', 1, 0)) AS any_c_or_offshore
    FROM posting_history p
    JOIN dim_work_centre w ON p.wc_id = w.wc_id
    GROUP BY p.emp_id
)
SELECT
    CASE
        WHEN COALESCE(h.cat_c_36m, 0) = 1 AND COALESCE(h.offshore_36m, 0) = 1 THEN 'Completed both Cat-C and offshore (>=36m)'
        WHEN COALESCE(h.cat_c_36m, 0) = 1 THEN 'Completed Cat-C only (>=36m)'
        WHEN COALESCE(h.offshore_36m, 0) = 1 THEN 'Completed offshore only (>=36m)'
        WHEN COALESCE(h.any_c_or_offshore, 0) = 1 THEN 'Served Cat-C/offshore but < 36 months'
        ELSE 'Never posted to Cat-C or offshore'
    END AS hard_tenure_status,
    (COALESCE(h.cat_c_36m, 0) = 0 AND COALESCE(h.offshore_36m, 0) = 0) AS never_completed_mandatory_tenure,
    COUNT(DISTINCT o.emp_id) AS overdue_executives,
    ROUND(COUNT(DISTINCT o.emp_id) * 100.0 / SUM(COUNT(DISTINCT o.emp_id)) OVER (), 1) AS pct_of_overdue
FROM overdue o
LEFT JOIN hist h ON o.emp_id = h.emp_id
GROUP BY 1, 2
ORDER BY never_completed_mandatory_tenure DESC, overdue_executives DESC;
