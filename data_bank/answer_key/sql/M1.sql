-- Answer Key SQL: M1
-- Question: "What is the total headcount by asset?" (aggregate, non-identifying)
-- Type: data
-- Semantic audit 2026-10-20: Old SQL summed 12 monthly headcount snapshots for FY26 vs 1 for FY21 (Eastern Offshore '12,312', +1,182%) for 4 hand-picked assets and answered a growth question.
-- Semantic audit 2026-10-20: Now: headcount by asset at the latest snapshot (30-Sep-2026) for all 14 operating assets, with 31-Mar-2026 and share of company.

WITH hc AS (
    SELECT
        h.wc_id,
        SUM(IF(h.month = '2026-09', h.headcount, 0)) AS hc_sep26,
        SUM(IF(h.month = '2026-03', h.headcount, 0)) AS hc_mar26
    FROM headcount_snapshot h
    WHERE h.month IN ('2026-03', '2026-09')
    GROUP BY h.wc_id
),
company AS (
    SELECT SUM(headcount) AS company_hc_sep26
    FROM headcount_snapshot
    WHERE month = '2026-09'
)
SELECT
    wc.wc_id,
    wc.short_name AS asset,
    wc.sector,
    wc.onshore_offshore,
    hc.hc_sep26 AS headcount_30sep2026,
    hc.hc_mar26 AS headcount_31mar2026,
    ROUND(hc.hc_sep26 * 100.0 / c.company_hc_sep26, 1) AS pct_of_company,
    c.company_hc_sep26
FROM dim_work_centre wc
JOIN hc ON hc.wc_id = wc.wc_id
CROSS JOIN company c
WHERE LOWER(wc.type) = 'asset'
ORDER BY headcount_30sep2026 DESC;
