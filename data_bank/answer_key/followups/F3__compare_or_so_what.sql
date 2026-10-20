-- Answer Key Follow-up SQL: F3__compare_or_so_what
-- Question: How do 5-year cumulative revenues and operating cash flows compare between Western Offshore and Onshore Gujarat assets?
-- Type: data
-- Semantic audit 2026-10-20: was all 8 basins; now only the two segments asked: Western Offshore Basin (Mumbai High,
-- Semantic audit 2026-10-20: Neelam & Heera, Bassein) vs Onshore Gujarat (Western Onshore Basin: Ankleshwar, Ahmedabad,
-- Semantic audit 2026-10-20: Mehsana, Cambay), FY22-FY26 cumulative. Operating cash flow proxied by EBITDA (no cash-flow
-- Semantic audit 2026-10-20: data at field level); production in BOE for per-barrel comparison.

SELECT
    CASE f.basin
        WHEN 'Western Offshore Basin' THEN 'Western Offshore'
        WHEN 'Western Onshore Basin' THEN 'Onshore Gujarat'
    END AS segment,
    COUNT(DISTINCT pnl.field_id) AS fields,
    ROUND(SUM(pnl.gross_revenue_inr_cr), 0) AS revenue_5yr_cr,
    ROUND(SUM(pnl.ebitda_inr_cr), 0) AS ebitda_ocf_proxy_5yr_cr,
    ROUND(SUM(pnl.ebitda_inr_cr) * 100 / SUM(pnl.gross_revenue_inr_cr), 1) AS ebitda_margin_pct,
    ROUND(SUM(pnl.total_production_boe) / 1e6, 1) AS production_5yr_mmboe,
    ROUND(SUM(pnl.ebitda_inr_cr) * 1e7 / SUM(pnl.total_production_boe), 0) AS ebitda_inr_per_boe
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
WHERE pnl.fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
  AND LOWER(pnl.line_type) = 'field'
  AND f.basin IN ('Western Offshore Basin', 'Western Onshore Basin')
GROUP BY segment
ORDER BY revenue_5yr_cr DESC;
