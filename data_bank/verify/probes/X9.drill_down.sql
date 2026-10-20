-- Probe ID: X9.drill_down
-- Parent ID: X9
-- Answer Type: sql
-- Question: List all CSR initiatives in NITI Aayog aspirational districts by theme and budget.
-- Personas: CMD
-- Tables: csr_projects
-- Drill Dims: csr_projects.csr_theme
-- Story IDs: S28
-- Expected Output: table
-- Handcrafted: true

SELECT
    csr_theme,
    COUNT(csr_project_id) AS projects_count,
    SUM(actual_disbursed_inr_cr) AS total_csr_spend
FROM csr_projects
WHERE is_aspirational_district = TRUE AND fiscal_year IN ('FY26', '2026')
GROUP BY csr_theme
ORDER BY total_csr_spend DESC;
