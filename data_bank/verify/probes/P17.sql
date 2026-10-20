-- Probe ID: P17
-- Parent ID: None
-- Answer Type: sql_plus_rag
-- Question: Does our dividend policy allow a higher payout this year, given the capex plan?
-- Personas: CMD, Director (Finance)
-- Tables: corporate_financials, capex_budget
-- Drill Dims: 
-- Story IDs: S30
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 13.25 (fy26_dividend_per_share_inr)
-- Expected Range: 11.93 - 14.58 (tolerance: ±10.0%)

SELECT
    fiscal_year,
    pat_inr_cr,
    total_dividend_payout_inr_cr,
    dividend_per_share_inr
FROM corporate_financials
WHERE fiscal_year IN ('FY26', '2026');
