-- Probe ID: X4
-- Parent ID: None
-- Answer Type: sql_plus_rag
-- Question: What are our total post-retirement benefit liabilities (PRBS, PRMB, gratuity) and what is the funding status?
-- Personas: CMD, Director (Finance)
-- Tables: benefit_liabilities
-- Drill Dims: benefit_liabilities.scheme_type
-- Story IDs: S32
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 21540.0 (total_retirement_benefit_obligations_cr)
-- Expected Range: 19386.0 - 23694.0 (tolerance: ±10.0%)

SELECT
    scheme_type,
    SUM(actuarial_liability_inr_cr) AS actuarial_liability_cr,
    SUM(plan_assets_inr_cr) AS plan_assets_cr,
    SUM(net_liability_inr_cr) AS net_liability_cr,
    ROUND(AVG(funded_ratio_pct), 1) AS avg_funded_ratio_pct
FROM benefit_liabilities
WHERE fiscal_year IN ('FY26', '2026')
GROUP BY scheme_type
ORDER BY actuarial_liability_cr DESC;
