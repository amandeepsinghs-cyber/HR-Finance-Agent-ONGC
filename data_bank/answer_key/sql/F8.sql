-- Answer Key SQL: F8
-- Question: What is the finding & development cost and reserve replacement ratio, by basin?
-- Type: data
-- Semantic audit 2026-10-20: RRR was an unweighted AVG of field ratios; now basin RRR = SUM(2P accretion) / SUM(production)
-- Semantic audit 2026-10-20: (MMTOE, FY26), F&D costs accretion-weighted, plus production, accretion and a company row.

WITH b AS (
    SELECT
        basin_name,
        SUM(annual_production_mmtoe) AS prod,
        SUM(gross_reserves_accretion_mmtoe) AS acc,
        SUM(finding_cost_usd_per_boe * gross_reserves_accretion_mmtoe) AS fc_x,
        SUM(development_cost_usd_per_boe * gross_reserves_accretion_mmtoe) AS dc_x,
        SUM(reserves_2p_total_mmtoe) AS r2p
    FROM reserves_annual
    WHERE fiscal_year = 'FY26'
    GROUP BY basin_name
),
u AS (
    SELECT * FROM b
    UNION ALL
    SELECT 'ALL BASINS', SUM(prod), SUM(acc), SUM(fc_x), SUM(dc_x), SUM(r2p) FROM b
)
SELECT
    basin_name,
    ROUND(prod, 2) AS production_mmtoe,
    ROUND(acc, 2) AS reserve_accretion_2p_mmtoe,
    ROUND(acc / NULLIF(prod, 0), 2) AS rrr_2p,
    ROUND(fc_x / NULLIF(acc, 0), 2) AS finding_cost_usd_boe,
    ROUND(dc_x / NULLIF(acc, 0), 2) AS development_cost_usd_boe,
    ROUND((fc_x + dc_x) / NULLIF(acc, 0), 2) AS fd_cost_usd_boe,
    ROUND(r2p, 1) AS reserves_2p_mmtoe
FROM u
ORDER BY basin_name = 'ALL BASINS', fd_cost_usd_boe DESC;
