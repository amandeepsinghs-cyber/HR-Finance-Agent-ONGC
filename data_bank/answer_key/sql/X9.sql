-- Answer Key SQL: X9
-- Question: CSR spend by state and theme vs. the policy's priority areas
-- Type: data
-- Semantic audit 2026-10-20: Adds the policy-priority dimension (CSR Policy 2025 cl.1.1: preference to Operational Areas; aspirational
-- districts): FY26 spend by state and theme with operational-area and aspirational-district spend.
SELECT
    g.state_name,
    c.csr_theme,
    COUNT(*) AS projects,
    ROUND(SUM(c.actual_disbursed_inr_cr), 2) AS spend_cr,
    ROUND(SUM(IF(c.is_operational_field_area, c.actual_disbursed_inr_cr, 0)), 2) AS operational_area_spend_cr,
    ROUND(SUM(IF(c.is_aspirational_district, c.actual_disbursed_inr_cr, 0)), 2) AS aspirational_district_spend_cr,
    g.ongc_operational_presence AS state_has_ongc_operations
FROM csr_projects c
JOIN dim_geography g ON c.state_code = g.state_code
WHERE c.fiscal_year = 'FY26'
GROUP BY g.state_name, c.csr_theme, g.ongc_operational_presence
ORDER BY spend_cr DESC;
