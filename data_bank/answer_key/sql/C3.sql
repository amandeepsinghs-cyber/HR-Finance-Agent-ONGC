-- Answer Key SQL: C3
-- Question: Which areas saw no headcount increase in the last 5 years, and which saw the most?
-- Type: data
-- Semantic audit 2026-10-20: (1) headcount_snapshot is a monthly stock - the old SQL SUMmed 12 FY26 months
-- against the single FY21 (March) snapshot, inflating growth ~10x (e.g. Eastern Offshore 960 -> 12,312,
-- +1,182%); (2) it hard-coded four work centres, so it could not say which areas saw no increase. Now: every
-- work centre, period-end snapshots 31-Mar-2021 (month '2021-03') vs 31-Mar-2026 (month '2026-03'), with a
-- flag for "no increase" (change <= 0). Ordered by absolute change, largest first.

WITH hc AS (
    SELECT
        wc_id,
        SUM(CASE WHEN month = '2021-03' THEN headcount END) AS hc_mar21,
        SUM(CASE WHEN month = '2026-03' THEN headcount END) AS hc_mar26
    FROM headcount_snapshot
    WHERE month IN ('2021-03', '2026-03')
    GROUP BY wc_id
)
SELECT
    wc.wc_id,
    wc.short_name,
    wc.type AS wc_type,
    wc.sector,
    COALESCE(h.hc_mar21, 0) AS hc_mar21,
    COALESCE(h.hc_mar26, 0) AS hc_mar26,
    COALESCE(h.hc_mar26, 0) - COALESCE(h.hc_mar21, 0) AS hc_change,
    ROUND((COALESCE(h.hc_mar26, 0) - h.hc_mar21) * 100.0 / NULLIF(h.hc_mar21, 0), 1) AS growth_pct,
    (COALESCE(h.hc_mar26, 0) - COALESCE(h.hc_mar21, 0)) <= 0 AS no_increase
FROM hc h
JOIN dim_work_centre wc ON h.wc_id = wc.wc_id
ORDER BY hc_change DESC, growth_pct DESC;
