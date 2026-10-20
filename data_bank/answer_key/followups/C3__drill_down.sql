-- Answer Key Follow-up SQL: C3__drill_down
-- Question: Break down the 5-year headcount trajectory of Rajahmundry, Eastern Offshore, Mehsana, and Cambay by executive vs non-executive.
-- Type: data
-- Semantic audit 2026-10-20: old SQL SUMmed headcount_snapshot over all months of FY21 (1 month) and FY26
-- (12 months) - FY26 values were 12 monthly stocks added together (e.g. Cambay executives 507 -> 3,913).
-- Now: March period-end snapshot for each year 2021..2026 (a true 5-year trajectory), by cadre from dim_grade.

SELECT
    wc.short_name,
    g.cadre,
    SUM(CASE WHEN h.month = '2021-03' THEN h.headcount END) AS hc_mar21,
    SUM(CASE WHEN h.month = '2022-03' THEN h.headcount END) AS hc_mar22,
    SUM(CASE WHEN h.month = '2023-03' THEN h.headcount END) AS hc_mar23,
    SUM(CASE WHEN h.month = '2024-03' THEN h.headcount END) AS hc_mar24,
    SUM(CASE WHEN h.month = '2025-03' THEN h.headcount END) AS hc_mar25,
    SUM(CASE WHEN h.month = '2026-03' THEN h.headcount END) AS hc_mar26,
    SUM(CASE WHEN h.month = '2026-03' THEN h.headcount END) - SUM(CASE WHEN h.month = '2021-03' THEN h.headcount END) AS change_5yr,
    ROUND((SUM(CASE WHEN h.month = '2026-03' THEN h.headcount END) - SUM(CASE WHEN h.month = '2021-03' THEN h.headcount END)) * 100.0
          / NULLIF(SUM(CASE WHEN h.month = '2021-03' THEN h.headcount END), 0), 1) AS change_pct
FROM headcount_snapshot h
JOIN dim_work_centre wc ON h.wc_id = wc.wc_id
JOIN dim_grade g ON h.grade_id = g.grade_id
WHERE wc.wc_id IN ('WC-EAS', 'WC-RAJ', 'WC-MEH', 'WC-CAM')
  AND h.month IN ('2021-03', '2022-03', '2023-03', '2024-03', '2025-03', '2026-03')
GROUP BY wc.short_name, g.cadre
ORDER BY wc.short_name, g.cadre;
