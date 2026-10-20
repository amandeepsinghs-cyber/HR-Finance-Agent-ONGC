-- Answer Key SQL: X5
-- Question: How did ONGC Videsh, MRPL and HPCL contribute to group profit and dividend?
-- Type: data
-- Semantic audit 2026-10-20: Restricted to the three entities asked (old SQL included OTPC and OPAL) and adds the contribution metrics:
-- ONGC-attributable PAT (PAT x equity holding), its share of FY26 consolidated PAT, and dividend received as a share of
-- ONGC standalone PAT.
SELECT
    s.entity_code,
    s.entity_name,
    s.ongc_equity_holding_pct,
    s.pat_inr_cr AS pat_cr,
    ROUND(s.pat_inr_cr * s.ongc_equity_holding_pct / 100, 1) AS ongc_share_of_pat_cr,
    ROUND(s.pat_inr_cr * s.ongc_equity_holding_pct / c.consolidated_pat_inr_cr, 1) AS share_of_group_pat_pct,
    s.dividend_received_by_ongc_inr_cr AS dividend_received_by_ongc_cr,
    ROUND(s.dividend_received_by_ongc_inr_cr * 100 / c.pat_inr_cr, 1) AS dividend_as_pct_of_ongc_standalone_pat,
    c.consolidated_pat_inr_cr AS group_consolidated_pat_cr,
    c.pat_inr_cr AS ongc_standalone_pat_cr
FROM subsidiary_financials s
JOIN corporate_financials c ON c.fiscal_year = s.fiscal_year
WHERE s.fiscal_year = 'FY26' AND s.entity_code IN ('OVL', 'MRPL', 'HPCL')
ORDER BY ongc_share_of_pat_cr DESC;
