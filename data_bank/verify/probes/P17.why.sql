-- Probe ID: P17.why
-- Parent ID: P17
-- Answer Type: sql_plus_rag
-- Question: What capital expenditure commitments (₹35,878 cr capex) and debt obligations constrain increasing the dividend payout ratio?
-- Personas: CMD, Director (Finance)
-- Tables: corporate_financials, capex_budget
-- Drill Dims: 
-- Story IDs: S30
-- Expected Output: table
-- Handcrafted: true

SELECT
    fiscal_year,
    pat_inr_cr,
    total_dividend_payout_inr_cr,
    dividend_per_share_inr
FROM corporate_financials
WHERE fiscal_year IN ('FY26', '2026');
