-- Answer Key Follow-up SQL: M1__compare_or_so_what
-- Question: How does the total workforce in Western Onshore assets compare with Eastern Offshore installations?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL compared summed snapshots (12 FY26 months vs 1 FY21 month) by whole sector, giving impossible growth rates.
-- Semantic audit 2026-10-20: Now: Western Onshore assets vs Eastern Offshore assets, period-end headcount at 31-Mar-2021, 31-Mar-2026 and 30-Sep-2026.

SELECT
    CASE WHEN LOWER(wc.sector) = 'western' THEN 'Western Onshore' ELSE 'Eastern Offshore' END AS asset_group,
    COUNT(DISTINCT wc.wc_id) AS assets,
    STRING_AGG(DISTINCT wc.short_name, ', ') AS asset_names,
    SUM(IF(h.month = '2021-03', h.headcount, 0)) AS hc_31mar2021,
    SUM(IF(h.month = '2026-03', h.headcount, 0)) AS hc_31mar2026,
    SUM(IF(h.month = '2026-09', h.headcount, 0)) AS hc_30sep2026,
    ROUND((SUM(IF(h.month = '2026-03', h.headcount, 0)) - SUM(IF(h.month = '2021-03', h.headcount, 0))) * 100.0
          / NULLIF(SUM(IF(h.month = '2021-03', h.headcount, 0)), 0), 1) AS change_mar21_to_mar26_pct
FROM headcount_snapshot h
JOIN dim_work_centre wc ON wc.wc_id = h.wc_id
WHERE LOWER(wc.type) = 'asset'
  AND h.month IN ('2021-03', '2026-03', '2026-09')
  AND ((LOWER(wc.sector) = 'western' AND LOWER(wc.onshore_offshore) = 'onshore')
       OR (LOWER(wc.sector) = 'eastern' AND LOWER(wc.onshore_offshore) = 'offshore'))
GROUP BY asset_group
ORDER BY hc_30sep2026 DESC;
