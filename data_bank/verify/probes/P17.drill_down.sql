-- Probe ID: P17.drill_down
-- Parent ID: P17
-- Answer Type: sql
-- Question: What was the interim and final dividend paid per share over the last 3 fiscal years?
-- Personas: Director (Finance)
-- Tables: corporate_financials
-- Drill Dims: corporate_financials.fiscal_year
-- Story IDs: S30
-- Expected Output: table
-- Handcrafted: true

SELECT
    fiscal_year,
    dividend_per_share_inr,
    total_dividend_payout_inr_cr,
    dividend_payout_ratio_pct
FROM corporate_financials
ORDER BY fiscal_year;
