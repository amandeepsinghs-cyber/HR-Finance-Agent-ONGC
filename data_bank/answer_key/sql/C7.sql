-- Answer Key SQL: C7
-- Question: Where have we invested the most capex in the last 5 years, and which fields are under-invested relative to their reserves?
-- Type: data
-- Semantic audit 2026-10-20: WRONG_QUESTION - the old SQL was a copy of C9 (project cost overruns, 360
-- milestone-duplicated rows) and contained no capex history or reserves. Now: actual capex FY22-FY26 (last 5
-- full FYs; capex_budget, all 12 months each) by asset, its share of the 5-year total, FY26 2P reserves
-- (reserves_annual, a balance -> FY26 only, footnote rows with NULL fiscal_year excluded), capex per MMTOE of
-- 2P reserves, and an under-invested flag = capex intensity below half the average of reserve-holding assets.
-- GAP: capex is recorded by asset/project, not by field, so under-investment is assessed at asset level; the
-- asset's largest 2P field is shown for reference.

WITH capex AS (
    SELECT asset_wc_id, SUM(actual_spend_inr_cr) AS capex_5yr_cr
    FROM capex_budget
    WHERE fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
    GROUP BY asset_wc_id
),
res AS (
    SELECT asset_wc_id, SUM(reserves_2p_total_mmtoe) AS reserves_2p_mmtoe,
           ARRAY_AGG(field_id ORDER BY reserves_2p_total_mmtoe DESC LIMIT 1)[OFFSET(0)] AS top_field_id
    FROM reserves_annual
    WHERE fiscal_year = 'FY26'
    GROUP BY asset_wc_id
),
j AS (
    SELECT c.asset_wc_id, c.capex_5yr_cr, r.reserves_2p_mmtoe, r.top_field_id
    FROM capex c LEFT JOIN res r ON r.asset_wc_id = c.asset_wc_id
),
avg_int AS (
    SELECT SUM(capex_5yr_cr) / NULLIF(SUM(reserves_2p_mmtoe), 0) AS cr_per_mmtoe_avg
    FROM j WHERE reserves_2p_mmtoe > 0
)
SELECT
    w.short_name AS asset,
    w.type AS wc_type,
    ROUND(j.capex_5yr_cr, 0) AS capex_fy22_fy26_cr,
    ROUND(j.capex_5yr_cr * 100.0 / SUM(j.capex_5yr_cr) OVER (), 1) AS pct_of_5yr_capex,
    ROUND(j.reserves_2p_mmtoe, 1) AS reserves_2p_mmtoe_fy26,
    ROUND(j.reserves_2p_mmtoe * 100.0 / SUM(j.reserves_2p_mmtoe) OVER (), 1) AS pct_of_2p_reserves,
    ROUND(j.capex_5yr_cr / NULLIF(j.reserves_2p_mmtoe, 0), 1) AS capex_cr_per_mmtoe_2p,
    ROUND(a.cr_per_mmtoe_avg, 1) AS avg_capex_cr_per_mmtoe_2p,
    (j.reserves_2p_mmtoe > 0 AND j.capex_5yr_cr / j.reserves_2p_mmtoe < 0.5 * a.cr_per_mmtoe_avg) AS under_invested,
    f.name AS largest_2p_field
FROM j
CROSS JOIN avg_int a
JOIN dim_work_centre w ON w.wc_id = j.asset_wc_id
LEFT JOIN dim_field f ON f.field_id = j.top_field_id
ORDER BY j.capex_5yr_cr DESC;
