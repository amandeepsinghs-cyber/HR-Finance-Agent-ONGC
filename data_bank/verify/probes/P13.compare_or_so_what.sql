-- Probe ID: P13.compare_or_so_what
-- Parent ID: P13
-- Answer Type: sql
-- Question: How much financial headroom in crore remains under the 30% cap based on the FY26 executive payroll?
-- Personas: Director (Finance)
-- Tables: benefit_liabilities, payroll_monthly
-- Drill Dims: 
-- Story IDs: S26
-- Expected Output: number
-- Handcrafted: true

SELECT
    scheme_name,
    dpe_30pct_superannuation_compliance_flag,
    annual_payout_inr_cr
FROM benefit_liabilities
WHERE fiscal_year IN ('FY26', '2026')
ORDER BY scheme_name;
