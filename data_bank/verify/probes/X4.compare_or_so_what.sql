-- Probe ID: X4.compare_or_so_what
-- Parent ID: X4
-- Answer Type: sql
-- Question: How does our overall funding ratio across employee benefit trusts compare with statutory requirements?
-- Personas: Director (Finance)
-- Tables: benefit_liabilities
-- Drill Dims: benefit_liabilities.scheme_type
-- Story IDs: S32
-- Expected Output: table
-- Handcrafted: true

SELECT
    scheme_type,
    ROUND(AVG(funded_ratio_pct), 1) AS funded_ratio_pct,
    dpe_30pct_superannuation_compliance_flag
FROM benefit_liabilities
WHERE fiscal_year IN ('FY26', '2026')
GROUP BY scheme_type, dpe_30pct_superannuation_compliance_flag
ORDER BY scheme_type;
