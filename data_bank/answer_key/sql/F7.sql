-- Answer Key SQL: F7
-- Question: What is the employee cost as a percentage of revenue, by asset, and how has it trended?
-- Type: data
-- Semantic audit 2026-10-20: grouped by asset name AND field values, so it returned one row per field labelled with the
-- Semantic audit 2026-10-20: asset name (295 rows, several per asset-year; corporate/plant lines with zero revenue mixed
-- Semantic audit 2026-10-20: in). Now aggregated to asset (field lines only): allocated manpower cost / gross revenue
-- Semantic audit 2026-10-20: for each FY21-FY26 (5-year trend) plus FY26 cost and revenue and the FY21->FY26 change.

WITH a AS (
    SELECT
        pnl.asset_wc_id,
        pnl.fiscal_year,
        SUM(pnl.allocated_manpower_cost_inr_cr) AS mp,
        SUM(pnl.gross_revenue_inr_cr) AS rev
    FROM field_pnl_annual pnl
    WHERE LOWER(pnl.line_type) = 'field'
      AND pnl.fiscal_year IN ('FY21', 'FY22', 'FY23', 'FY24', 'FY25', 'FY26')
    GROUP BY pnl.asset_wc_id, pnl.fiscal_year
)
SELECT
    wc.short_name AS asset_name,
    wc.onshore_offshore,
    ROUND(SUM(IF(a.fiscal_year = 'FY26', a.mp, 0)), 1) AS manpower_cost_fy26_cr,
    ROUND(SUM(IF(a.fiscal_year = 'FY26', a.rev, 0)), 0) AS revenue_fy26_cr,
    ROUND(SAFE_DIVIDE(SUM(IF(a.fiscal_year = 'FY21', a.mp, 0)), SUM(IF(a.fiscal_year = 'FY21', a.rev, 0))) * 100, 1) AS pct_fy21,
    ROUND(SAFE_DIVIDE(SUM(IF(a.fiscal_year = 'FY22', a.mp, 0)), SUM(IF(a.fiscal_year = 'FY22', a.rev, 0))) * 100, 1) AS pct_fy22,
    ROUND(SAFE_DIVIDE(SUM(IF(a.fiscal_year = 'FY23', a.mp, 0)), SUM(IF(a.fiscal_year = 'FY23', a.rev, 0))) * 100, 1) AS pct_fy23,
    ROUND(SAFE_DIVIDE(SUM(IF(a.fiscal_year = 'FY24', a.mp, 0)), SUM(IF(a.fiscal_year = 'FY24', a.rev, 0))) * 100, 1) AS pct_fy24,
    ROUND(SAFE_DIVIDE(SUM(IF(a.fiscal_year = 'FY25', a.mp, 0)), SUM(IF(a.fiscal_year = 'FY25', a.rev, 0))) * 100, 1) AS pct_fy25,
    ROUND(SAFE_DIVIDE(SUM(IF(a.fiscal_year = 'FY26', a.mp, 0)), SUM(IF(a.fiscal_year = 'FY26', a.rev, 0))) * 100, 1) AS pct_fy26,
    ROUND((SAFE_DIVIDE(SUM(IF(a.fiscal_year = 'FY26', a.mp, 0)), SUM(IF(a.fiscal_year = 'FY26', a.rev, 0)))
         - SAFE_DIVIDE(SUM(IF(a.fiscal_year = 'FY21', a.mp, 0)), SUM(IF(a.fiscal_year = 'FY21', a.rev, 0)))) * 100, 1) AS change_fy21_fy26_pp
FROM a
JOIN dim_work_centre wc ON a.asset_wc_id = wc.wc_id
GROUP BY wc.short_name, wc.onshore_offshore
ORDER BY pct_fy26 DESC;
