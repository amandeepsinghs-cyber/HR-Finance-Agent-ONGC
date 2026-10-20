-- Answer Key Follow-up SQL: X5__drill_down
-- Question: What were the individual net profit (PAT) contributions and dividend dividends declared by OVL, MRPL, and HPCL in FY26?
-- Type: data
-- Semantic audit 2026-10-20: Returns the PAT and dividend declared the question asks for (old SQL returned only dividend received,
-- for five entities), plus payout ratio and ONGC's receipt.
SELECT
    entity_code,
    entity_name,
    pat_inr_cr AS pat_cr,
    dividend_declared_inr_cr AS dividend_declared_cr,
    ROUND(dividend_declared_inr_cr * 100 / pat_inr_cr, 1) AS payout_ratio_pct,
    dividend_received_by_ongc_inr_cr AS dividend_received_by_ongc_cr
FROM subsidiary_financials
WHERE fiscal_year = 'FY26' AND entity_code IN ('OVL', 'MRPL', 'HPCL')
ORDER BY pat_cr DESC;
