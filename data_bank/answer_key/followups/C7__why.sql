-- Answer Key Follow-up SQL: C7__why
-- Question: Why did fields with substantial 2P oil/gas reserves receive less development drilling capex than planned in the BE/RE cycles?
-- Type: data
-- Semantic audit 2026-10-20: old SQL added reserves_2p_oil_mmt + reserves_2p_gas_bcm (MMT + BCM) and called it
-- MMTOE, and had no capex or BE/RE data at all. Now: FY22-FY26 development-drilling capex by asset - Budget
-- Estimate (BE), Revised Estimate (RE), actual, actual vs BE and vs RE, utilisation - for assets holding FY26
-- 2P reserves (reserves_2p_total_mmtoe, the canonical oil-equivalent column), with development cost per BOE
-- (reserve-weighted). GAP: capex is not recorded by field, and there is no recorded reason code for
-- under-spend, so the answer shows where and by how much spend fell short, not the stated cause.

WITH dd AS (
    SELECT asset_wc_id,
           SUM(budget_estimate_be_inr_cr) AS be_cr,
           SUM(revised_estimate_re_inr_cr) AS re_cr,
           SUM(actual_spend_inr_cr) AS actual_cr
    FROM capex_budget
    WHERE fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
      AND LOWER(capex_head) = 'development_drilling'
    GROUP BY asset_wc_id
),
res AS (
    SELECT asset_wc_id,
           SUM(reserves_2p_total_mmtoe) AS reserves_2p_mmtoe,
           SUM(development_cost_usd_per_boe * reserves_2p_total_mmtoe) / NULLIF(SUM(reserves_2p_total_mmtoe), 0) AS dev_cost_usd_boe
    FROM reserves_annual
    WHERE fiscal_year = 'FY26'
    GROUP BY asset_wc_id
)
SELECT
    w.short_name AS asset,
    ROUND(r.reserves_2p_mmtoe, 1) AS reserves_2p_mmtoe_fy26,
    ROUND(dd.be_cr, 0) AS dev_drilling_be_cr,
    ROUND(dd.re_cr, 0) AS dev_drilling_re_cr,
    ROUND(dd.actual_cr, 0) AS dev_drilling_actual_cr,
    ROUND(dd.actual_cr - dd.be_cr, 0) AS actual_vs_be_cr,
    ROUND(dd.actual_cr - dd.re_cr, 0) AS actual_vs_re_cr,
    ROUND(dd.actual_cr * 100.0 / NULLIF(dd.be_cr, 0), 1) AS utilisation_vs_be_pct,
    ROUND(dd.actual_cr / NULLIF(r.reserves_2p_mmtoe, 0), 1) AS dev_capex_cr_per_mmtoe,
    ROUND(r.dev_cost_usd_boe, 2) AS dev_cost_usd_boe
FROM res r
JOIN dim_work_centre w ON w.wc_id = r.asset_wc_id
LEFT JOIN dd ON dd.asset_wc_id = r.asset_wc_id
ORDER BY r.reserves_2p_mmtoe DESC;
