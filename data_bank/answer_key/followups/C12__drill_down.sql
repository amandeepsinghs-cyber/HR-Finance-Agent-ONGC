-- Answer Key Follow-up SQL: C12__drill_down
-- Question: Break down the manpower cost per BOE for Mumbai High, Neelam-Heera, Ahmedabad, and Assam into executive vs non-executive payroll.
-- Type: data
-- Semantic audit 2026-10-20: old SQL averaged field-level USD/BOE ratios (unweighted) and had no executive /
-- non-executive split at all. field_pnl_annual has no cadre split, so the split uses FY26 payroll_monthly
-- gross salary by work centre and dim_grade.cadre (the same basis as hrfin_gold.mart_asset_productivity
-- payroll_cost_inr_cr), divided by the asset's FY26 production (production_monthly, 12 months); USD at the
-- FY26 average INR/USD from dim_price_fx.

WITH pay AS (
    SELECT p.wc_id, g.cadre, SUM(p.gross_salary_inr) / 1e7 AS payroll_cr, COUNT(DISTINCT p.emp_id) AS employees_paid
    FROM payroll_monthly p
    JOIN dim_grade g ON p.grade_id = g.grade_id
    WHERE p.fiscal_year = 'FY26' AND p.wc_id IN ('WC-MUM', 'WC-NEH', 'WC-AHM', 'WC-ASM')
    GROUP BY 1, 2
),
prod AS (
    SELECT asset_wc_id AS wc_id, SUM(total_production_boe) AS boe
    FROM production_monthly
    WHERE fiscal_year = 'FY26' AND asset_wc_id IN ('WC-MUM', 'WC-NEH', 'WC-AHM', 'WC-ASM')
    GROUP BY 1
),
fx AS (SELECT AVG(inr_usd_fx_rate) AS fx FROM dim_price_fx WHERE fiscal_year = 'FY26')
SELECT
    wc.short_name AS asset,
    pay.cadre,
    pay.employees_paid,
    ROUND(pay.payroll_cr, 1) AS payroll_inr_cr,
    ROUND(prod.boe / 1e6, 2) AS mmboe_fy26,
    ROUND(pay.payroll_cr * 1e7 / NULLIF(prod.boe, 0), 0) AS payroll_inr_per_boe,
    ROUND(pay.payroll_cr * 1e7 / NULLIF(prod.boe, 0) / fx.fx, 2) AS payroll_usd_per_boe,
    ROUND(pay.payroll_cr * 100.0 / SUM(pay.payroll_cr) OVER (PARTITION BY pay.wc_id), 1) AS pct_of_asset_payroll
FROM pay
JOIN prod ON prod.wc_id = pay.wc_id
JOIN dim_work_centre wc ON wc.wc_id = pay.wc_id
CROSS JOIN fx
ORDER BY SUM(pay.payroll_cr) OVER (PARTITION BY pay.wc_id) * 1e7 / prod.boe DESC, asset, pay.cadre;
