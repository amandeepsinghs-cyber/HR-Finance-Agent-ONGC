-- Probe ID: P15.compare_or_so_what
-- Parent ID: P15
-- Answer Type: sql
-- Question: How much CSR expenditure was directed toward operational field areas versus non-operational aspirational districts?
-- Personas: Director (Finance)
-- Tables: csr_projects
-- Drill Dims: csr_projects.is_operational_field_area
-- Story IDs: S28
-- Expected Output: table
-- Handcrafted: true

SELECT
    is_operational_field_area,
    is_aspirational_district,
    SUM(actual_disbursed_inr_cr) AS total_csr_spend
FROM csr_projects
WHERE fiscal_year IN ('FY26', '2026')
GROUP BY is_operational_field_area, is_aspirational_district
ORDER BY total_csr_spend DESC;
