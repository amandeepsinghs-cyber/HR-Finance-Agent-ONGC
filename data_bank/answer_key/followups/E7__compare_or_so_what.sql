-- Answer Key Follow-up SQL: E7__compare_or_so_what
-- Question: How does last year's net profit compare with the previous 3-year average annual earnings?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL returned four yearly values with no 3-year average. Now one row: FY26 PAT vs FY23-FY25 average, gap and %.

SELECT
    MAX(IF(fiscal_year = 'FY26', pat_inr_cr, NULL)) AS fy26_pat_inr_cr,
    ROUND(AVG(IF(fiscal_year IN ('FY23', 'FY24', 'FY25'), pat_inr_cr, NULL)), 1) AS avg_fy23_fy25_pat_inr_cr,
    ROUND(MAX(IF(fiscal_year = 'FY26', pat_inr_cr, NULL)) - AVG(IF(fiscal_year IN ('FY23', 'FY24', 'FY25'), pat_inr_cr, NULL)), 1) AS gap_inr_cr,
    ROUND((MAX(IF(fiscal_year = 'FY26', pat_inr_cr, NULL)) - AVG(IF(fiscal_year IN ('FY23', 'FY24', 'FY25'), pat_inr_cr, NULL))) * 100.0
          / AVG(IF(fiscal_year IN ('FY23', 'FY24', 'FY25'), pat_inr_cr, NULL)), 1) AS gap_pct
FROM corporate_financials
WHERE fiscal_year IN ('FY23', 'FY24', 'FY25', 'FY26');
