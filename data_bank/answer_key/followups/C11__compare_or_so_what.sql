-- Answer Key Follow-up SQL: C11__compare_or_so_what
-- Question: How does the labor productivity (BOE per employee) in expanding assets compare with the ONGC corporate average?
-- Type: data
-- Semantic audit 2026-10-20: old SQL took an unweighted AVG of field-level boe_per_employee for every work
-- centre in the field P&L (19 rows incl. plants/HQ with 0), with no notion of "expanding" assets. Now: the 15
-- producing assets with FY26 BOE / 31-Mar-2026 headcount (period-end snapshot), a flag for assets whose
-- headcount grew between Mar-21 and Mar-26 ("expanding"), and two corporate averages as ratios of sums:
-- all producing assets, and company-wide (FY26 BOE / total company headcount at 31-Mar-2026 = 23,117).

WITH hc AS (
    SELECT wc_id,
           SUM(IF(month = '2021-03', headcount, 0)) AS hc_mar21,
           SUM(IF(month = '2026-03', headcount, 0)) AS hc_mar26
    FROM headcount_snapshot
    WHERE month IN ('2021-03', '2026-03')
    GROUP BY wc_id
),
prod AS (
    SELECT asset_wc_id AS wc_id, SUM(total_production_boe) AS boe26
    FROM production_monthly WHERE fiscal_year = 'FY26' GROUP BY 1
),
a AS (
    SELECT wc.short_name, h.hc_mar21, h.hc_mar26, p.boe26, h.hc_mar26 > h.hc_mar21 AS is_expanding
    FROM prod p JOIN hc h ON h.wc_id = p.wc_id JOIN dim_work_centre wc ON wc.wc_id = p.wc_id
),
u AS (
    SELECT short_name, 0 AS ord, is_expanding, hc_mar21, hc_mar26, boe26 FROM a
    UNION ALL
    SELECT 'Corporate average - producing assets', 1, NULL, SUM(hc_mar21), SUM(hc_mar26), SUM(boe26) FROM a
    UNION ALL
    SELECT 'Corporate average - whole company', 2, NULL,
           (SELECT SUM(hc_mar21) FROM hc), (SELECT SUM(hc_mar26) FROM hc), (SELECT SUM(boe26) FROM prod)
)
SELECT
    short_name,
    is_expanding,
    hc_mar21,
    hc_mar26,
    ROUND(boe26 / 1e6, 2) AS mmboe_fy26,
    ROUND(boe26 / NULLIF(hc_mar26, 0), 0) AS boe_per_employee_fy26
FROM u
ORDER BY ord, is_expanding DESC, boe_per_employee_fy26 DESC;
