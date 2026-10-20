-- Probe ID: P15.drill_down
-- Parent ID: P15
-- Answer Type: sql
-- Question: Break down CSR spending by state (Assam, Gujarat, UP, AP) and by thematic sector (healthcare, education, water).
-- Personas: Director (Finance)
-- Tables: csr_projects, dim_geography
-- Drill Dims: dim_geography.state_name, csr_projects.csr_theme
-- Story IDs: S28
-- Expected Output: table
-- Handcrafted: true

SELECT
    g.state_name,
    c.csr_theme,
    SUM(c.actual_disbursed_inr_cr) AS total_csr_spend
FROM csr_projects c
JOIN dim_geography g ON c.state_code = g.state_code
WHERE c.fiscal_year IN ('FY26', '2026')
GROUP BY g.state_name, c.csr_theme
ORDER BY total_csr_spend DESC;
