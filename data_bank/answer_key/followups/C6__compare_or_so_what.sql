-- Answer Key Follow-up SQL: C6__compare_or_so_what
-- Question: How do the profit margins of Mumbai High and Bassein compare with onshore assets like Ankleshwar and Mehsana?
-- Type: data
-- Semantic audit 2026-10-20: old SQL listed EBITDA of all 53 fields (no margins, no asset grouping). Now:
-- FY26 asset-level totals (field lines only) for Mumbai High, Bassein & Satellite, Ankleshwar and Mehsana,
-- with EBITDA and PBT margins computed on summed revenue (ratio of sums, not average of field ratios).

SELECT
    wc.short_name AS asset,
    wc.onshore_offshore,
    COUNT(*) AS fields,
    ROUND(SUM(pnl.gross_revenue_inr_cr), 1) AS gross_revenue_inr_cr,
    ROUND(SUM(pnl.ebitda_inr_cr), 1) AS ebitda_inr_cr,
    ROUND(SUM(pnl.pbt_inr_cr), 1) AS pbt_inr_cr,
    ROUND(SUM(pnl.ebitda_inr_cr) * 100.0 / NULLIF(SUM(pnl.gross_revenue_inr_cr), 0), 1) AS ebitda_margin_pct,
    ROUND(SUM(pnl.pbt_inr_cr) * 100.0 / NULLIF(SUM(pnl.gross_revenue_inr_cr), 0), 1) AS pbt_margin_pct,
    ROUND(SUM(pnl.total_opex_inr_cr) * 1e7 / NULLIF(SUM(pnl.total_production_boe), 0), 0) AS opex_inr_per_boe
FROM field_pnl_annual pnl
JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
WHERE pnl.fiscal_year = 'FY26'
  AND LOWER(pnl.line_type) = 'field'
  AND pnl.asset_wc_id IN ('WC-MUM', 'WC-BAS', 'WC-ANK', 'WC-MEH')
GROUP BY wc.short_name, wc.onshore_offshore
ORDER BY ebitda_margin_pct DESC;
