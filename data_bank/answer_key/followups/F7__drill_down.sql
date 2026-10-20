-- Answer Key Follow-up SQL: F7__drill_down
-- Question: Which low-revenue, mature onshore assets have an employee cost exceeding 25% of gross field revenue?
-- Type: data
-- Semantic audit 2026-10-20: listed all 59 FY26 lines (offshore, plant and corporate included) with no 25% threshold and
-- Semantic audit 2026-10-20: field rows labelled as assets. Now FY26 mature onshore fields whose allocated manpower cost
-- Semantic audit 2026-10-20: exceeds 25% of gross field revenue, with their asset-level ratio for context.

WITH asset AS (
    SELECT asset_wc_id,
           SUM(allocated_manpower_cost_inr_cr) * 100 / SUM(gross_revenue_inr_cr) AS asset_pct,
           SUM(gross_revenue_inr_cr) AS asset_rev
    FROM field_pnl_annual
    WHERE fiscal_year = 'FY26' AND LOWER(line_type) = 'field'
    GROUP BY asset_wc_id
)
SELECT
    f.name AS field_name,
    wc.short_name AS asset_name,
    ROUND(pnl.gross_revenue_inr_cr, 1) AS revenue_fy26_cr,
    ROUND(pnl.allocated_manpower_cost_inr_cr, 1) AS manpower_cost_fy26_cr,
    ROUND(pnl.allocated_manpower_cost_inr_cr * 100 / pnl.gross_revenue_inr_cr, 1) AS manpower_pct_revenue,
    pnl.regular_employee_headcount,
    ROUND(a.asset_pct, 1) AS asset_manpower_pct_revenue,
    ROUND(a.asset_rev, 0) AS asset_revenue_fy26_cr
FROM field_pnl_annual pnl
JOIN dim_field f ON f.field_id = pnl.field_id
JOIN dim_work_centre wc ON wc.wc_id = pnl.asset_wc_id
JOIN asset a ON a.asset_wc_id = pnl.asset_wc_id
WHERE pnl.fiscal_year = 'FY26'
  AND LOWER(pnl.line_type) = 'field'
  AND LOWER(f.onshore_offshore) = 'onshore'
  AND LOWER(f.maturity) = 'mature'
  AND pnl.allocated_manpower_cost_inr_cr > 0.25 * pnl.gross_revenue_inr_cr
ORDER BY manpower_pct_revenue DESC;
