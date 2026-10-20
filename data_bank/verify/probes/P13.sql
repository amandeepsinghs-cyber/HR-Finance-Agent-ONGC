-- Probe ID: P13
-- Parent ID: None
-- Answer Type: sql_plus_rag
-- Question: Are we within the DPE 30% superannuation cap on benefits? How much headroom is left?
-- Personas: Director (Finance)
-- Tables: benefit_liabilities, payroll_monthly
-- Drill Dims: 
-- Story IDs: S26
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 30.0 (dpe_superannuation_cap_pct)
-- Expected Range: 27.0 - 33.0 (tolerance: ±10.0%)

SELECT
    fiscal_year,
    scheme_name,
    annual_payout_inr_cr,
    dpe_30pct_superannuation_compliance_flag
FROM benefit_liabilities
WHERE fiscal_year IN ('FY26', '2026')
ORDER BY annual_payout_inr_cr DESC;
