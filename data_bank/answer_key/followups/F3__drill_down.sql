-- Answer Key Follow-up SQL: F3__drill_down
-- Question: Which fields have demonstrated improving EBITDA margins despite natural decline in reservoir pressure?
-- Type: data
-- Semantic audit 2026-10-20: was FY26 fields sorted by lowest EBITDA (no trend, no decline test). Now fields whose
-- Semantic audit 2026-10-20: production (BOE, proxy for natural decline; no reservoir-pressure column exists) fell
-- Semantic audit 2026-10-20: FY22->FY26 while EBITDA margin rose over the same 5-year window used by parent F3.

WITH x AS (
    SELECT
        pnl.field_id,
        SUM(IF(pnl.fiscal_year = 'FY22', pnl.total_production_boe, 0)) AS boe22,
        SUM(IF(pnl.fiscal_year = 'FY26', pnl.total_production_boe, 0)) AS boe26,
        SUM(IF(pnl.fiscal_year = 'FY22', pnl.ebitda_inr_cr, 0)) AS e22,
        SUM(IF(pnl.fiscal_year = 'FY26', pnl.ebitda_inr_cr, 0)) AS e26,
        SUM(IF(pnl.fiscal_year = 'FY22', pnl.gross_revenue_inr_cr, 0)) AS r22,
        SUM(IF(pnl.fiscal_year = 'FY26', pnl.gross_revenue_inr_cr, 0)) AS r26
    FROM field_pnl_annual pnl
    WHERE pnl.fiscal_year IN ('FY22', 'FY26') AND LOWER(pnl.line_type) = 'field'
    GROUP BY pnl.field_id
)
SELECT
    f.name AS field_name,
    w.short_name AS asset_name,
    f.maturity,
    ROUND((x.boe26 - x.boe22) * 100 / NULLIF(x.boe22, 0), 1) AS production_change_pct,
    ROUND(x.e22 * 100 / NULLIF(x.r22, 0), 1) AS ebitda_margin_fy22_pct,
    ROUND(x.e26 * 100 / NULLIF(x.r26, 0), 1) AS ebitda_margin_fy26_pct,
    ROUND(x.e26 * 100 / NULLIF(x.r26, 0) - x.e22 * 100 / NULLIF(x.r22, 0), 1) AS margin_change_pp,
    ROUND(x.e26, 1) AS ebitda_fy26_cr
FROM x
JOIN dim_field f ON f.field_id = x.field_id
JOIN dim_work_centre w ON w.wc_id = f.asset_wc_id
WHERE x.boe22 > 0 AND x.r22 > 0
  AND x.boe26 < x.boe22
  AND x.e26 / NULLIF(x.r26, 0) > x.e22 / x.r22
ORDER BY margin_change_pp DESC;
