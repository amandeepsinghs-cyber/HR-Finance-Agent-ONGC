-- Probe ID: W4
-- Parent ID: None
-- Answer Type: what_if_sim
-- Question: If the windfall tax is removed, how much does net realisation per barrel improve?
-- Personas: Director (Finance)
-- Tables: corporate_financials, price_fx_monthly, production_monthly
-- Drill Dims: 
-- Story IDs: S21
-- Expected Output: number
-- Handcrafted: true
-- Story Target: 13034.0 (oidb_cess_fy26_cr)
-- Expected Range: 11730.6 - 14337.4 (tolerance: ±10.0%)

SELECT
    fiscal_year,
    saed_windfall_tax_inr_cr,
    ebitda_inr_cr
FROM corporate_financials
WHERE fiscal_year IN ('FY26', '2026');
