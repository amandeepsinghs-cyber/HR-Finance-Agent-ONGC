-- Answer Key Follow-up SQL: X1__compare_or_so_what
-- Question: How does the contractor cost per BOE compare with regular employee cost across onshore and offshore assets?
-- Type: data
-- Semantic audit 2026-10-20: Onshore vs offshore producing assets, FY26: contractor cost per BOE vs regular manpower cost per BOE,
-- both computed as total cost / total BOE. Old SQL joined field_pnl (field grain) to monthly contract rows (fan-out),
-- averaged per-row ratios and included 31 non-producing work centres.
WITH fx AS (
    SELECT AVG(inr_usd_fx_rate) AS fx FROM price_fx_monthly WHERE fiscal_year = 'FY26'
),
prod AS (
    SELECT asset_wc_id AS wc_id, SUM(total_production_boe) AS boe
    FROM production_monthly WHERE fiscal_year = 'FY26' GROUP BY asset_wc_id
),
cw_cost AS (
    SELECT wc_id, SUM(monthly_cost_inr) / 1e7 AS contractor_cost_cr
    FROM contract_workforce WHERE fiscal_year = 'FY26' GROUP BY wc_id
),
mp AS (
    SELECT asset_wc_id AS wc_id, SUM(allocated_manpower_cost_inr_cr) AS regular_cost_cr
    FROM field_pnl_annual WHERE fiscal_year = 'FY26' AND LOWER(line_type) = 'field' GROUP BY asset_wc_id
)
SELECT
    w.onshore_offshore,
    COUNT(*) AS producing_assets,
    ROUND(SUM(prod.boe) / 1e6, 2) AS mmboe_fy26,
    ROUND(SUM(cw_cost.contractor_cost_cr), 1) AS contractor_cost_fy26_cr,
    ROUND(SUM(mp.regular_cost_cr), 1) AS regular_manpower_cost_fy26_cr,
    ROUND(SUM(cw_cost.contractor_cost_cr) * 1e7 / ANY_VALUE(fx.fx) / SUM(prod.boe), 3) AS contractor_cost_per_boe_usd,
    ROUND(SUM(mp.regular_cost_cr) * 1e7 / ANY_VALUE(fx.fx) / SUM(prod.boe), 2) AS regular_cost_per_boe_usd,
    ROUND(SUM(mp.regular_cost_cr) / SUM(cw_cost.contractor_cost_cr), 1) AS regular_to_contractor_cost_multiple
FROM prod
CROSS JOIN fx
JOIN dim_work_centre w ON w.wc_id = prod.wc_id
LEFT JOIN cw_cost ON cw_cost.wc_id = prod.wc_id
LEFT JOIN mp ON mp.wc_id = prod.wc_id
GROUP BY w.onshore_offshore
ORDER BY regular_cost_per_boe_usd;
