-- Probe ID: P13.drill_down
-- Parent ID: P13
-- Answer Type: sql
-- Question: What are the annual payouts and actuarial liabilities across PRBS pension, PRMB medical, gratuity, and leave encashment?
-- Personas: Director (Finance)
-- Tables: benefit_liabilities, payroll_monthly
-- Drill Dims: benefit_liabilities.scheme_type
-- Story IDs: S26
-- Expected Output: table
-- Handcrafted: true

SELECT
    scheme_type,
    actuarial_liability_inr_cr,
    annual_payout_inr_cr,
    dpe_30pct_superannuation_compliance_flag
FROM benefit_liabilities
WHERE fiscal_year IN ('FY26', '2026')
ORDER BY scheme_type;
