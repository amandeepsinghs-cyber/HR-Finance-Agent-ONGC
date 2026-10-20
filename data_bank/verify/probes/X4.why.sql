-- Probe ID: X4.why
-- Parent ID: X4
-- Answer Type: sql_plus_rag
-- Question: Why has the net liability for PRMB medical benefits increased in recent actuarial valuations?
-- Personas: Director (Finance)
-- Tables: benefit_liabilities
-- Drill Dims: benefit_liabilities.fiscal_year
-- Story IDs: S32
-- Expected Output: table
-- Handcrafted: true

SELECT
    fiscal_year,
    actuarial_liability_inr_cr,
    annual_payout_inr_cr,
    medical_inflation_rate_pct
FROM benefit_liabilities
WHERE scheme_type LIKE '%Medical%'
ORDER BY fiscal_year;
