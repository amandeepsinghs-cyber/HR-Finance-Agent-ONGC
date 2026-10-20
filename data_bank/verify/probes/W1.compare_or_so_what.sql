-- Probe ID: W1.compare_or_so_what
-- Parent ID: W1
-- Answer Type: what_if_sim
-- Question: What would be the overall reduction in ONGC's annual EBITDA and operating cash flows if crude averages 0/bbl?
-- Personas: CMD, Director (Finance)
-- Tables: corporate_financials
-- Drill Dims: corporate_financials.fiscal_year
-- Story IDs: S15
-- Expected Output: number
-- Handcrafted: true

SELECT
    cf.fiscal_year,
    cf.ebitda_inr_cr AS baseline_fy26_ebitda_cr,
    ROUND(cf.ebitda_inr_cr - 8450.0, 2) AS stressed_ebitda_cr,
    8450.0 AS estimated_ebitda_reduction_cr
FROM corporate_financials cf
WHERE cf.fiscal_year IN ('FY26', '2026')
ORDER BY cf.fiscal_year DESC
LIMIT 1;
