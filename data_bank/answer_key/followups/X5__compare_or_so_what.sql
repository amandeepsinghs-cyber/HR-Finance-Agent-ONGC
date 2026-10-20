-- Answer Key Follow-up SQL: X5__compare_or_so_what
-- Question: How does the consolidated return on capital employed (ROCE) compare with ONGC standalone domestic upstream ROCE?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL summed subsidiary PAT by year and never touched ROCE. Now consolidated vs standalone ROCE
-- FY22-FY26 from corporate_financials, with the gap.
SELECT
    fiscal_year,
    standalone_roce_pct,
    consolidated_roce_pct,
    ROUND(consolidated_roce_pct - standalone_roce_pct, 2) AS consolidated_minus_standalone_pp,
    pat_inr_cr AS standalone_pat_cr,
    consolidated_pat_inr_cr AS consolidated_pat_cr
FROM corporate_financials
WHERE fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
ORDER BY fiscal_year;
