-- Answer Key Follow-up SQL: F2__drill_down
-- Question: Which offshore and onshore projects show the largest underspend or overspend against their Budget Estimates (BE)?
-- Type: data
-- Semantic audit 2026-10-20: was FY26 (parent is the current year), grouped by project name, no offshore/onshore split.
-- Semantic audit 2026-10-20: Now FY27 YTD (Apr-Sep 2026) by prj_id with segment; top-3 overspend and top-3 underspend
-- Semantic audit 2026-10-20: projects per segment (offshore / onshore) ranked on actual - BE.

WITH p AS (
    SELECT
        cb.prj_id,
        dp.name AS project_name,
        wc.short_name AS asset_name,
        LOWER(wc.onshore_offshore) AS segment,
        SUM(cb.budget_estimate_be_inr_cr) AS be,
        SUM(cb.actual_spend_inr_cr) AS actual
    FROM capex_budget cb
    JOIN dim_project dp ON dp.prj_id = cb.prj_id
    LEFT JOIN dim_work_centre wc ON wc.wc_id = cb.asset_wc_id
    WHERE cb.fiscal_year = 'FY27'
    GROUP BY cb.prj_id, dp.name, wc.short_name, wc.onshore_offshore
),
r AS (
    SELECT *,
        actual - be AS variance,
        ROW_NUMBER() OVER (PARTITION BY segment ORDER BY actual - be DESC) AS rk_over,
        ROW_NUMBER() OVER (PARTITION BY segment ORDER BY actual - be ASC) AS rk_under
    FROM p
    WHERE segment IN ('offshore', 'onshore')
)
SELECT
    segment,
    IF(variance >= 0, 'overspend', 'underspend') AS direction,
    prj_id,
    project_name,
    asset_name,
    ROUND(be, 1) AS be_ytd_cr,
    ROUND(actual, 1) AS actual_ytd_cr,
    ROUND(variance, 1) AS variance_vs_be_cr,
    ROUND(variance * 100 / NULLIF(be, 0), 1) AS variance_vs_be_pct
FROM r
WHERE (rk_over <= 3 AND variance > 0) OR rk_under <= 3
ORDER BY segment, variance_vs_be_cr;
