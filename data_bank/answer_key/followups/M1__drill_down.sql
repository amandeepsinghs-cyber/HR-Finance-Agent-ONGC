-- Answer Key Follow-up SQL: M1__drill_down
-- Question: What is the breakdown of total headcount by executive versus non-executive cadre across assets?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL summed all 12 FY26 monthly snapshots (person-months) across all 46 work centres.
-- Semantic audit 2026-10-20: Now: executive vs non-executive headcount per operating asset at the 30-Sep-2026 snapshot (same population as M1).

SELECT
    wc.short_name AS asset,
    SUM(IF(LOWER(g.cadre) = 'executive', h.headcount, 0)) AS executive_hc,
    SUM(IF(LOWER(g.cadre) = 'non_executive', h.headcount, 0)) AS non_executive_hc,
    SUM(h.headcount) AS total_hc,
    ROUND(SUM(IF(LOWER(g.cadre) = 'executive', h.headcount, 0)) * 100.0 / NULLIF(SUM(h.headcount), 0), 1) AS executive_share_pct
FROM headcount_snapshot h
JOIN dim_work_centre wc ON wc.wc_id = h.wc_id
JOIN dim_grade g ON g.grade_id = h.grade_id
WHERE h.month = '2026-09'
  AND LOWER(wc.type) = 'asset'
GROUP BY wc.short_name
ORDER BY total_hc DESC;
