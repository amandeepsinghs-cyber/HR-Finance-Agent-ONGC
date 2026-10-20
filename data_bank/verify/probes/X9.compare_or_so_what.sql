-- Probe ID: X9.compare_or_so_what
-- Parent ID: X9
-- Answer Type: sql
-- Question: How does our CSR spend in aspirational districts compare with the 60% operational area guideline?
-- Personas: CMD
-- Tables: csr_projects
-- Drill Dims: csr_projects.is_aspirational_district
-- Story IDs: S28
-- Expected Output: table
-- Handcrafted: true

SELECT
    is_aspirational_district,
    SUM(actual_disbursed_inr_cr) AS total_csr_spend
FROM csr_projects
WHERE fiscal_year IN ('FY26', '2026')
GROUP BY is_aspirational_district;
