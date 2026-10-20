-- Answer Key Follow-up SQL: C12__why
-- Question: Why is manpower cost per BOE significantly higher at mature, low-volume onshore fields compared to offshore assets?
-- Type: data
-- Semantic audit 2026-10-20: old SQL compared simple AVERAGES of field-level USD/BOE ratios by onshore/offshore
-- (7.91 vs 3.60), which over-weights tiny fields. Now FY26 field P&L lines grouped by onshore/offshore x
-- maturity with ratios of sums: manpower cost per BOE, output per field, BOE per regular employee and
-- manpower cost per employee - separating the volume effect (BOE per head) from the pay effect (cost per head).

WITH fx AS (SELECT AVG(inr_usd_fx_rate) AS fx FROM dim_price_fx WHERE fiscal_year = 'FY26')
SELECT
    f.onshore_offshore,
    f.maturity,
    COUNT(*) AS fields,
    ROUND(SUM(pnl.total_production_boe) / 1e6, 2) AS mmboe_fy26,
    ROUND(SUM(pnl.total_production_boe) / 1e6 / COUNT(*), 2) AS mmboe_per_field,
    SUM(pnl.regular_employee_headcount) AS regular_headcount,
    ROUND(SUM(pnl.total_production_boe) / NULLIF(SUM(pnl.regular_employee_headcount), 0), 0) AS boe_per_employee,
    ROUND(SUM(pnl.allocated_manpower_cost_inr_cr) * 100.0 / NULLIF(SUM(pnl.regular_employee_headcount), 0), 1) AS manpower_cost_per_employee_inr_lakh,
    ROUND(SUM(pnl.allocated_manpower_cost_inr_cr) * 1e7 / NULLIF(SUM(pnl.total_production_boe), 0) / ANY_VALUE(fx.fx), 2) AS manpower_cost_usd_per_boe
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
CROSS JOIN fx
WHERE pnl.fiscal_year = 'FY26' AND LOWER(pnl.line_type) = 'field'
GROUP BY f.onshore_offshore, f.maturity
ORDER BY manpower_cost_usd_per_boe DESC;
