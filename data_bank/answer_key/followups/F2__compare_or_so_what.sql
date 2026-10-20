-- Answer Key Follow-up SQL: F2__compare_or_so_what
-- Question: How does our year-to-date capex burn rate compare with the historical expenditure curve at the end of Q2?
-- Type: data
-- Semantic audit 2026-10-20: compared full-year FY22-FY26 totals (12 months) with nothing for the current year. Now
-- Semantic audit 2026-10-20: H1 (Apr-Sep, end of Q2) spend for every FY22-FY27 year, H1 spend as % of H1 BE, and for
-- Semantic audit 2026-10-20: completed years H1 as % of full-year actual (the historical expenditure curve).

SELECT
    fiscal_year,
    COUNT(DISTINCT IF(SUBSTR(month, 6, 2) IN ('04', '05', '06', '07', '08', '09'), month, NULL)) AS h1_months,
    ROUND(SUM(IF(SUBSTR(month, 6, 2) IN ('04', '05', '06', '07', '08', '09'), budget_estimate_be_inr_cr, 0)), 1) AS h1_be_cr,
    ROUND(SUM(IF(SUBSTR(month, 6, 2) IN ('04', '05', '06', '07', '08', '09'), actual_spend_inr_cr, 0)), 1) AS h1_actual_cr,
    ROUND(SUM(IF(SUBSTR(month, 6, 2) IN ('04', '05', '06', '07', '08', '09'), actual_spend_inr_cr, 0)) * 100
          / NULLIF(SUM(IF(SUBSTR(month, 6, 2) IN ('04', '05', '06', '07', '08', '09'), budget_estimate_be_inr_cr, 0)), 0), 1) AS h1_utilisation_vs_be_pct,
    IF(COUNT(DISTINCT month) = 12, ROUND(SUM(actual_spend_inr_cr), 1), NULL) AS full_year_actual_cr,
    IF(COUNT(DISTINCT month) = 12,
       ROUND(SUM(IF(SUBSTR(month, 6, 2) IN ('04', '05', '06', '07', '08', '09'), actual_spend_inr_cr, 0)) * 100 / SUM(actual_spend_inr_cr), 1),
       NULL) AS h1_share_of_full_year_pct
FROM capex_budget
WHERE fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26', 'FY27')
GROUP BY fiscal_year
ORDER BY fiscal_year;
