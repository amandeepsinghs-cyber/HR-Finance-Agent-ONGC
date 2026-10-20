-- Probe ID: X9
-- Parent ID: None
-- Answer Type: sql_plus_rag
-- Question: What CSR projects are active in aspirational districts, and what is our total spend in operational states?
-- Personas: CMD
-- Tables: csr_projects, dim_geography
-- Drill Dims: dim_geography.state_name, csr_projects.csr_theme
-- Story IDs: S28
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 652.0 (statutory_csr_obligation_cr)
-- Expected Range: 586.8 - 717.2 (tolerance: ±10.0%)

SELECT
    g.state_name,
    c.csr_theme,
    SUM(c.actual_disbursed_inr_cr) AS total_csr_spend
FROM csr_projects c
JOIN dim_geography g ON c.state_code = g.state_code
WHERE c.fiscal_year IN ('FY26', '2026')
GROUP BY g.state_name, c.csr_theme
ORDER BY total_csr_spend DESC;
