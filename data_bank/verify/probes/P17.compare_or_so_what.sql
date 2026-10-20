-- Probe ID: P17.compare_or_so_what
-- Parent ID: P17
-- Answer Type: sql
-- Question: How does our dividend payout compare against the DIPAM minimum requirement (5% of net worth or 30% of PAT)?
-- Personas: Director (Finance)
-- Tables: corporate_financials
-- Drill Dims: corporate_financials.fiscal_year
-- Story IDs: S30
-- Expected Output: table
-- Handcrafted: true

SELECT
    fiscal_year,
    pat_inr_cr,
    total_dividend_payout_inr_cr,
    ROUND((total_dividend_payout_inr_cr * 100.0) / NULLIF(pat_inr_cr, 0), 2) AS actual_payout_pct
FROM corporate_financials
ORDER BY fiscal_year;
