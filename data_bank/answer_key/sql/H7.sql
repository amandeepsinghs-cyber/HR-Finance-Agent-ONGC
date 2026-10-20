-- Answer Key SQL: H7
-- Question: What is women's representation by grade and asset, and what has it been for offshore postings?
-- Type: data
-- Semantic audit 2026-10-20: old SQL listed raw counts of women executives for the top-20 grade x WC cells (no share, no
-- denominator, nothing on offshore). Now: women's representation (% of active employees) by grade, by work location class,
-- by asset (type='asset'), and the offshore trend from March headcount snapshots (2021-03 ... 2026-03, latest 2026-09).
WITH act AS (
    SELECT e.emp_id, e.gender, e.current_grade_id, w.short_name, w.type, w.onshore_offshore, g.level_order
    FROM employee_master e
    JOIN dim_work_centre w ON w.wc_id = e.current_wc_id
    JOIN dim_grade g ON g.grade_id = e.current_grade_id
    WHERE LOWER(e.employment_status) = 'active'
),
offshore_trend AS (
    SELECT h.month, SUM(IF(LOWER(h.gender) = 'female', h.headcount, 0)) AS women, SUM(h.headcount) AS total
    FROM headcount_snapshot h
    JOIN dim_work_centre w ON w.wc_id = h.wc_id
    WHERE LOWER(w.onshore_offshore) = 'offshore'
      AND h.month IN ('2021-03', '2022-03', '2023-03', '2024-03', '2025-03', '2026-03', '2026-09')
    GROUP BY h.month
)
SELECT '1. Company' AS dimension, 'All active employees' AS label, 0 AS sort_key,
       COUNTIF(LOWER(gender) = 'female') AS women, COUNT(*) AS total,
       ROUND(COUNTIF(LOWER(gender) = 'female') * 100.0 / COUNT(*), 1) AS women_pct
FROM act
UNION ALL
SELECT '2. Grade', current_grade_id, MIN(level_order),
       COUNTIF(LOWER(gender) = 'female'), COUNT(*), ROUND(COUNTIF(LOWER(gender) = 'female') * 100.0 / COUNT(*), 1)
FROM act GROUP BY current_grade_id
UNION ALL
SELECT '3. Location class', onshore_offshore, 0,
       COUNTIF(LOWER(gender) = 'female'), COUNT(*), ROUND(COUNTIF(LOWER(gender) = 'female') * 100.0 / COUNT(*), 1)
FROM act GROUP BY onshore_offshore
UNION ALL
SELECT '4. Offshore trend (headcount snapshot)', month, 0, women, total, ROUND(women * 100.0 / total, 1)
FROM offshore_trend
UNION ALL
SELECT '5. Asset', short_name, 0,
       COUNTIF(LOWER(gender) = 'female'), COUNT(*), ROUND(COUNTIF(LOWER(gender) = 'female') * 100.0 / COUNT(*), 1)
FROM act WHERE LOWER(type) = 'asset' GROUP BY short_name
ORDER BY dimension, sort_key, label;
