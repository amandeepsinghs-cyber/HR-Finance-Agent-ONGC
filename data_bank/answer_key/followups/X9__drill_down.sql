-- Answer Key Follow-up SQL: X9__drill_down
-- Question: What proportion of our ₹949 cr CSR spend was allocated to education, healthcare, sanitation, and aspirational districts?
-- Type: data
-- Semantic audit 2026-10-20: Proportion of total FY26 spend by theme (old SQL returned only aspirational-district projects, i.e.
-- 222 of 949 cr, without proportions), with aspirational-district spend inside each theme.
SELECT
    csr_theme,
    COUNT(*) AS projects,
    ROUND(SUM(actual_disbursed_inr_cr), 2) AS spend_cr,
    ROUND(SUM(actual_disbursed_inr_cr) * 100 / SUM(SUM(actual_disbursed_inr_cr)) OVER (), 1) AS share_of_total_pct,
    ROUND(SUM(IF(is_aspirational_district, actual_disbursed_inr_cr, 0)), 2) AS aspirational_district_spend_cr,
    ROUND(SUM(SUM(actual_disbursed_inr_cr)) OVER (), 2) AS total_csr_spend_cr,
    ROUND(SUM(SUM(IF(is_aspirational_district, actual_disbursed_inr_cr, 0))) OVER (), 2) AS total_aspirational_spend_cr
FROM csr_projects
WHERE fiscal_year = 'FY26'
GROUP BY csr_theme
ORDER BY spend_cr DESC;
