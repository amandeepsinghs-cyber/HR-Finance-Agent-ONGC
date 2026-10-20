-- Answer Key Follow-up SQL: F7__why
-- Question: Why has employee cost per unit revenue risen faster in legacy onshore assets compared to high-volume offshore platforms?
-- Type: data
-- Semantic audit 2026-10-20: was a byte-for-byte copy of the drill-down SQL (FY26 per-field ratio). Now onshore vs offshore
-- Semantic audit 2026-10-20: field lines for FY22 (comparable Brent year) and FY26: manpower cost, revenue, production,
-- Semantic audit 2026-10-20: manpower cost per BOE, revenue per BOE, BOE per regular employee and manpower % revenue.

SELECT
    wc.onshore_offshore,
    pnl.fiscal_year,
    ROUND(SUM(pnl.allocated_manpower_cost_inr_cr), 0) AS manpower_cost_cr,
    ROUND(SUM(pnl.gross_revenue_inr_cr), 0) AS revenue_cr,
    ROUND(SUM(pnl.total_production_boe) / 1e6, 1) AS production_mmboe,
    SUM(pnl.regular_employee_headcount) AS regular_headcount,
    ROUND(SUM(pnl.allocated_manpower_cost_inr_cr) * 1e7 / SUM(pnl.total_production_boe), 0) AS manpower_inr_per_boe,
    ROUND(SUM(pnl.gross_revenue_inr_cr) * 1e7 / SUM(pnl.total_production_boe), 0) AS revenue_inr_per_boe,
    ROUND(SUM(pnl.total_production_boe) / NULLIF(SUM(pnl.regular_employee_headcount), 0), 0) AS boe_per_employee,
    ROUND(SUM(pnl.allocated_manpower_cost_inr_cr) * 100 / SUM(pnl.gross_revenue_inr_cr), 1) AS manpower_pct_revenue
FROM field_pnl_annual pnl
JOIN dim_work_centre wc ON wc.wc_id = pnl.asset_wc_id
WHERE LOWER(pnl.line_type) = 'field'
  AND pnl.fiscal_year IN ('FY22', 'FY26')
GROUP BY wc.onshore_offshore, pnl.fiscal_year
ORDER BY wc.onshore_offshore DESC, pnl.fiscal_year;
