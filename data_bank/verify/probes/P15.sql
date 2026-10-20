-- Probe ID: P15
-- Parent ID: None
-- Answer Type: sql_plus_rag
-- Question: What was our CSR expenditure in FY26, and did we meet the statutory 2% mandate?
-- Personas: CMD, Director (Finance)
-- Tables: csr_projects, dim_geography
-- Drill Dims: csr_projects.state_code
-- Story IDs: S28
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 652.0 (statutory_csr_obligation_cr)
-- Expected Range: 586.8 - 717.2 (tolerance: ±10.0%)

SELECT
    state_code,
    SUM(actual_disbursed_inr_cr) AS total_csr_spend
FROM csr_projects
WHERE fiscal_year IN ('FY26', '2026')
GROUP BY state_code
ORDER BY total_csr_spend DESC;
