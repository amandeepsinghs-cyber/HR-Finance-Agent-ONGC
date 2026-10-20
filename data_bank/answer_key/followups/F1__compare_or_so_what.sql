-- Answer Key Follow-up SQL: F1__compare_or_so_what
-- Question: How does the lifting cost of Mumbai High offshore compare with onshore assets and the overall company average ($11.5/BOE)?
-- Type: data
-- Semantic audit 2026-10-20: was an unweighted AVG by onshore/offshore only (Mumbai High never isolated). Now FY26
-- Semantic audit 2026-10-20: production-weighted $/BOE for Mumbai High, other offshore, onshore and all fields, next to
-- Semantic audit 2026-10-20: the $11.5 benchmark quoted in the question and the reported corporate lifting cost.

WITH f AS (
    SELECT
        CASE
            WHEN pnl.asset_wc_id = 'WC-MUM' THEN '1. Mumbai High'
            WHEN LOWER(wc.onshore_offshore) = 'offshore' THEN '2. Other offshore assets'
            ELSE '3. Onshore assets'
        END AS segment,
        pnl.total_production_boe AS boe,
        pnl.lifting_cost_per_boe_usd * pnl.total_production_boe AS usd_x_boe
    FROM field_pnl_annual pnl
    JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
    WHERE pnl.fiscal_year = 'FY26' AND LOWER(pnl.line_type) = 'field' AND pnl.total_production_boe > 0
),
seg AS (
    SELECT segment, SUM(boe) AS boe, SUM(usd_x_boe) AS usd_x_boe FROM f GROUP BY segment
    UNION ALL
    SELECT '4. All fields (company)', SUM(boe), SUM(usd_x_boe) FROM f
)
SELECT
    s.segment,
    ROUND(s.boe / 1e6, 2) AS production_mmboe,
    ROUND(s.usd_x_boe / s.boe, 2) AS lifting_cost_usd_boe,
    11.5 AS benchmark_usd_boe,
    ROUND(s.usd_x_boe / s.boe - 11.5, 2) AS gap_vs_benchmark_usd,
    cf.lifting_cost_average_usd_boe AS reported_corporate_lifting_usd_boe
FROM seg s
CROSS JOIN (SELECT lifting_cost_average_usd_boe FROM corporate_financials WHERE fiscal_year = 'FY26') cf
ORDER BY s.segment;
