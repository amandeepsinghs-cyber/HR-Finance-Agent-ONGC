-- Answer Key Follow-up SQL: F1__drill_down
-- Question: What are the individual cost components (power, workover, chemicals, surface repair, water handling) of lifting cost for the highest-cost asset?
-- Type: data
-- Semantic audit 2026-10-20: was total opex components for ALL assets ranked by absolute opex (Mumbai High), not the
-- Semantic audit 2026-10-20: highest-cost asset. Now picks the asset with the highest FY26 production-weighted $/BOE
-- Semantic audit 2026-10-20: (parent F1) and breaks its opex into components (cr, $/BOE, share). No separate
-- Semantic audit 2026-10-20: 'surface repair' column exists; repairs are inside workover_repairs (GAP noted).

WITH a AS (
    SELECT
        pnl.asset_wc_id,
        SUM(pnl.total_production_boe) AS boe,
        SUM(pnl.lifting_cost_per_boe_usd * pnl.total_production_boe) / SUM(pnl.total_production_boe) AS usd_boe,
        SUM(pnl.total_opex_inr_cr) AS opex,
        SUM(pnl.power_fuel_cost_inr_cr) AS power_fuel,
        SUM(pnl.workover_repairs_cost_inr_cr) AS workover_repairs,
        SUM(pnl.chemicals_consumables_cost_inr_cr) AS chemicals,
        SUM(pnl.water_handling_cost_inr_cr) AS water_handling,
        SUM(pnl.allocated_manpower_cost_inr_cr) AS manpower,
        SUM(pnl.contractor_cost_inr_cr) AS contractor,
        SUM(pnl.logistics_osv_chopper_cost_inr_cr) AS logistics,
        SUM(pnl.other_opex_inr_cr) AS other_opex
    FROM field_pnl_annual pnl
    WHERE pnl.fiscal_year = 'FY26' AND LOWER(pnl.line_type) = 'field' AND pnl.total_production_boe > 0
    GROUP BY pnl.asset_wc_id
),
top AS (
    SELECT * FROM a ORDER BY usd_boe DESC LIMIT 1
),
comp AS (
    SELECT asset_wc_id, boe, usd_boe, opex, component, cost_cr
    FROM top,
    UNNEST([
        STRUCT('power_fuel' AS component, power_fuel AS cost_cr),
        STRUCT('workover_repairs', workover_repairs),
        STRUCT('chemicals_consumables', chemicals),
        STRUCT('water_handling', water_handling),
        STRUCT('manpower_allocated', manpower),
        STRUCT('contractor', contractor),
        STRUCT('logistics_osv_chopper', logistics),
        STRUCT('other_opex', other_opex)
    ])
)
SELECT
    wc.short_name AS asset_name,
    ROUND(c.usd_boe, 2) AS asset_lifting_cost_usd_boe,
    c.component,
    ROUND(c.cost_cr, 1) AS cost_inr_cr,
    ROUND(c.cost_cr / c.opex * c.usd_boe, 2) AS component_usd_boe,
    ROUND(c.cost_cr * 100 / c.opex, 1) AS share_of_opex_pct,
    ROUND(c.opex, 1) AS total_opex_inr_cr
FROM comp c
JOIN dim_work_centre wc ON wc.wc_id = c.asset_wc_id
ORDER BY cost_inr_cr DESC;
