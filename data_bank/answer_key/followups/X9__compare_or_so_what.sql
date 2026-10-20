-- Answer Key Follow-up SQL: X9__compare_or_so_what
-- Question: How does the expenditure distribution across states compare with the statutory guideline prioritizing operational field areas?
-- Type: data
-- Semantic audit 2026-10-20: Distribution by operational-area status (old SQL split by aspirational flag, not the operational-area
-- guideline asked about). FY26 spend, projects and share.
SELECT
    CASE
        WHEN c.is_operational_field_area THEN '1: Operational field areas'
        WHEN g.ongc_operational_presence THEN '2: Non-operational district in an ONGC state'
        ELSE '3: State with no ONGC operations'
    END AS area_category,
    COUNT(*) AS projects,
    COUNT(DISTINCT c.state_code) AS states,
    ROUND(SUM(c.actual_disbursed_inr_cr), 2) AS spend_cr,
    ROUND(SUM(c.actual_disbursed_inr_cr) * 100 / SUM(SUM(c.actual_disbursed_inr_cr)) OVER (), 1) AS share_pct,
    ROUND(SUM(IF(c.is_aspirational_district, c.actual_disbursed_inr_cr, 0)), 2) AS of_which_aspirational_cr
FROM csr_projects c
JOIN dim_geography g ON c.state_code = g.state_code
WHERE c.fiscal_year = 'FY26'
GROUP BY area_category
ORDER BY area_category;
