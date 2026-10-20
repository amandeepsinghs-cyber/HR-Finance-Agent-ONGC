-- Answer Key Follow-up SQL: X9__why
-- Question: Why did certain non-operational states receive CSR project funding under national priority and disaster relief allocations?
-- Type: data
-- Semantic audit 2026-10-20: Replaces generic CSR-policy citations with the projects in question: FY26 projects outside operational
-- field areas, with district, theme and aspirational flag. GAP: the data carries no 'national priority' or 'disaster
-- relief' tag; the aspirational-district flag is the only national-priority marker.
SELECT
    g.state_name,
    c.district_name,
    c.project_name,
    c.csr_theme,
    c.is_aspirational_district,
    g.ongc_operational_presence AS state_has_ongc_operations,
    c.actual_disbursed_inr_cr AS spend_cr,
    c.wc_id AS sponsoring_wc
FROM csr_projects c
JOIN dim_geography g ON c.state_code = g.state_code
WHERE c.fiscal_year = 'FY26' AND NOT c.is_operational_field_area
ORDER BY spend_cr DESC;
