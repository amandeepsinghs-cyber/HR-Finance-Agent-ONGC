-- Answer Key Follow-up SQL: F1__why
-- Question: Why has the lifting cost in mature fields like Cambay and Mehsana increased over the last 3 fiscal years?
-- Type: data
-- Semantic audit 2026-10-20: was an unweighted AVG of field $/BOE with opex only (no drivers). Now production-weighted
-- Semantic audit 2026-10-20: $/BOE and Rs/BOE for FY24-FY26, with the drivers: production (MMboe), opex, manpower,
-- Semantic audit 2026-10-20: power and BOE-weighted water cut (production_monthly) - fixed costs over falling volume.

WITH pnl AS (
    SELECT
        asset_wc_id,
        fiscal_year,
        SUM(total_production_boe) AS boe,
        SUM(lifting_cost_per_boe_usd * total_production_boe) / SUM(total_production_boe) AS usd_boe,
        SUM(total_opex_inr_cr) AS opex,
        SUM(allocated_manpower_cost_inr_cr) AS manpower,
        SUM(power_fuel_cost_inr_cr) AS power_fuel,
        SUM(water_handling_cost_inr_cr) AS water_handling
    FROM field_pnl_annual
    WHERE asset_wc_id IN ('WC-CAM', 'WC-MEH')
      AND fiscal_year IN ('FY24', 'FY25', 'FY26')
      AND LOWER(line_type) = 'field'
    GROUP BY asset_wc_id, fiscal_year
),
wc AS (
    SELECT asset_wc_id, fiscal_year,
           SUM(water_cut_pct * total_production_boe) / SUM(total_production_boe) AS water_cut_pct
    FROM production_monthly
    WHERE asset_wc_id IN ('WC-CAM', 'WC-MEH') AND fiscal_year IN ('FY24', 'FY25', 'FY26')
    GROUP BY asset_wc_id, fiscal_year
)
SELECT
    w.short_name,
    p.fiscal_year,
    ROUND(p.usd_boe, 2) AS lifting_cost_usd_boe,
    ROUND(p.opex * 1e7 / p.boe, 0) AS lifting_cost_inr_boe,
    ROUND(p.boe / 1e6, 2) AS production_mmboe,
    ROUND(p.opex, 1) AS total_opex_cr,
    ROUND(p.manpower, 1) AS manpower_cost_cr,
    ROUND(p.power_fuel, 1) AS power_fuel_cr,
    ROUND(p.water_handling, 1) AS water_handling_cr,
    ROUND(x.water_cut_pct, 1) AS water_cut_pct
FROM pnl p
JOIN wc x USING (asset_wc_id, fiscal_year)
JOIN dim_work_centre w ON w.wc_id = p.asset_wc_id
ORDER BY w.short_name, p.fiscal_year;
