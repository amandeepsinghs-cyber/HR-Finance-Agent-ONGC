-- Answer Key Follow-up SQL: P15__drill_down
-- Question: What were the actual CSR expenditures in Assam, Gujarat, Maharashtra, and Andhra Pradesh against total CSR spend of ₹949 cr?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL returned every state x theme (26 rows) instead of the four states asked. Now the four
-- Semantic audit 2026-10-20: states with themes, their spend and share of the FY26 total (computed, not typed).
WITH t AS (SELECT SUM(actual_disbursed_inr_cr) AS total_cr FROM csr_projects WHERE fiscal_year = 'FY26')
SELECT
    g.state_name,
    STRING_AGG(DISTINCT c.csr_theme, '; ' ORDER BY c.csr_theme) AS csr_themes,
    COUNT(*) AS projects,
    ROUND(SUM(c.sanctioned_budget_inr_cr), 2) AS sanctioned_cr,
    ROUND(SUM(c.actual_disbursed_inr_cr), 2) AS csr_spend_cr,
    ROUND(100 * SUM(c.actual_disbursed_inr_cr) / ANY_VALUE(t.total_cr), 1) AS share_of_fy26_total_pct,
    ROUND(ANY_VALUE(t.total_cr), 2) AS fy26_total_spend_cr
FROM csr_projects c
JOIN dim_geography g ON g.state_code = c.state_code
CROSS JOIN t
WHERE c.fiscal_year = 'FY26' AND c.state_code IN ('AS', 'GJ', 'MH', 'AP')
GROUP BY g.state_name
ORDER BY csr_spend_cr DESC;
