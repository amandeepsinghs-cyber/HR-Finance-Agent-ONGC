-- Answer Key Follow-up SQL: F4__compare_or_so_what
-- Question: How does the statutory government take percentage on ONGC nomination fields compare with NELP/HELP revenue-sharing contracts?
-- Type: data
-- Semantic audit 2026-10-20: returned one FY26 levies/revenue ratio mislabelled 'gross_revenue_inr_cr'. Now field P&L
-- Semantic audit 2026-10-20: statutory take (royalty + OIDB cess + SAED) as % of gross revenue split by regime:
-- Semantic audit 2026-10-20: nomination (ONGC-operated) vs joint-venture fields (Panna, Mukta - the only non-nomination
-- Semantic audit 2026-10-20: fields), FY26 and FY22-FY26. GAP: no NELP/HELP blocks, profit-petroleum or revenue-share
-- Semantic audit 2026-10-20: data exist, so the JV PSC fields are the closest proxy and profit petroleum is excluded.

WITH op AS (
    SELECT field_id, ANY_VALUE(operatorship) AS operatorship
    FROM production_monthly
    GROUP BY field_id
),
p AS (
    SELECT
        CASE LOWER(op.operatorship) WHEN 'operated' THEN 'Nomination (ONGC-operated)' ELSE 'Joint venture / PSC (Panna-Mukta)' END AS regime,
        pnl.fiscal_year,
        pnl.field_id,
        pnl.gross_revenue_inr_cr AS rev,
        pnl.statutory_royalty_inr_cr AS royalty,
        pnl.statutory_cess_inr_cr AS cess,
        pnl.statutory_windfall_tax_saed_inr_cr AS saed
    FROM field_pnl_annual pnl
    JOIN op ON op.field_id = pnl.field_id
    WHERE LOWER(pnl.line_type) = 'field' AND pnl.fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
)
SELECT
    regime,
    COUNT(DISTINCT field_id) AS fields,
    ROUND(SUM(IF(fiscal_year = 'FY26', rev, 0)), 0) AS revenue_fy26_cr,
    ROUND(SUM(IF(fiscal_year = 'FY26', royalty, 0)) * 100 / SUM(IF(fiscal_year = 'FY26', rev, 0)), 1) AS royalty_pct_fy26,
    ROUND(SUM(IF(fiscal_year = 'FY26', cess, 0)) * 100 / SUM(IF(fiscal_year = 'FY26', rev, 0)), 1) AS cess_pct_fy26,
    ROUND(SUM(IF(fiscal_year = 'FY26', royalty + cess + saed, 0)) * 100 / SUM(IF(fiscal_year = 'FY26', rev, 0)), 1) AS govt_take_pct_fy26,
    ROUND(SUM(royalty + cess + saed) * 100 / SUM(rev), 1) AS govt_take_pct_fy22_fy26,
    ROUND(SUM(saed), 0) AS saed_fy22_fy26_cr
FROM p
GROUP BY regime
ORDER BY revenue_fy26_cr DESC;
