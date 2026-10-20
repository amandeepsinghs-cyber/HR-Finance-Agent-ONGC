-- Answer Key SQL: X1
-- Question: How many contract workers vs. regular employees per asset, and at what cost per BOE?
-- Type: data
-- Semantic audit 2026-10-20: Per producing asset: contract workers vs regular employees at 31-Mar-2026 (single month, not SUM of 12
-- monthly snapshots), FY26 contractor cost and regular manpower cost per BOE computed from cost / FY26 BOE (USD at FY26 avg FX).
-- Old SQL summed 12 monthly stocks (Ahmedabad 16,579 contractors vs 1,345 real), summed 12 headcount snapshots, used the
-- unreliable contractor_cost_per_boe_usd column (0 for producing Assam) and listed 46 non-producing work centres.
WITH fx AS (
    SELECT AVG(inr_usd_fx_rate) AS fx FROM price_fx_monthly WHERE fiscal_year = 'FY26'
),
prod AS (
    SELECT asset_wc_id AS wc_id, SUM(total_production_boe) AS boe_fy26
    FROM production_monthly WHERE fiscal_year = 'FY26' GROUP BY asset_wc_id
),
cw_mar AS (
    SELECT wc_id, SUM(contractor_headcount) AS contract_workers_mar26
    FROM contract_workforce WHERE month = '2026-03' GROUP BY wc_id
),
cw_cost AS (
    SELECT wc_id, SUM(monthly_cost_inr) / 1e7 AS contractor_cost_fy26_cr
    FROM contract_workforce WHERE fiscal_year = 'FY26' GROUP BY wc_id
),
reg AS (
    SELECT wc_id, SUM(headcount) AS regular_employees_mar26
    FROM headcount_snapshot WHERE month = '2026-03' GROUP BY wc_id
),
mp AS (
    SELECT asset_wc_id AS wc_id, SUM(allocated_manpower_cost_inr_cr) AS regular_manpower_cost_fy26_cr
    FROM field_pnl_annual WHERE fiscal_year = 'FY26' AND LOWER(line_type) = 'field' GROUP BY asset_wc_id
)
SELECT
    w.short_name,
    w.onshore_offshore,
    cw_mar.contract_workers_mar26,
    reg.regular_employees_mar26,
    ROUND(SAFE_DIVIDE(cw_mar.contract_workers_mar26, reg.regular_employees_mar26), 2) AS contract_to_regular_ratio,
    ROUND(cw_cost.contractor_cost_fy26_cr, 1) AS contractor_cost_fy26_cr,
    ROUND(mp.regular_manpower_cost_fy26_cr, 1) AS regular_manpower_cost_fy26_cr,
    ROUND(prod.boe_fy26 / 1e6, 2) AS mmboe_fy26,
    ROUND(cw_cost.contractor_cost_fy26_cr * 1e7 / fx.fx / prod.boe_fy26, 3) AS contractor_cost_per_boe_usd,
    ROUND(mp.regular_manpower_cost_fy26_cr * 1e7 / fx.fx / prod.boe_fy26, 2) AS regular_cost_per_boe_usd
FROM prod
CROSS JOIN fx
JOIN dim_work_centre w ON w.wc_id = prod.wc_id
LEFT JOIN cw_mar ON cw_mar.wc_id = prod.wc_id
LEFT JOIN cw_cost ON cw_cost.wc_id = prod.wc_id
LEFT JOIN reg ON reg.wc_id = prod.wc_id
LEFT JOIN mp ON mp.wc_id = prod.wc_id
ORDER BY cw_mar.contract_workers_mar26 DESC;
