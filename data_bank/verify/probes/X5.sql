-- Probe ID: X5
-- Parent ID: None
-- Answer Type: sql
-- Question: How do the financial performances and dividend payouts of our major subsidiaries (HPCL, MRPL, OVL) compare?
-- Personas: CMD, Director (Finance)
-- Tables: subsidiary_financials
-- Drill Dims: subsidiary_financials.entity_name
-- Story IDs: S33
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 32894.0 (standalone_pat_fy26_cr)
-- Expected Range: 29604.6 - 36183.4 (tolerance: ±10.0%)

SELECT
    entity_name,
    revenue_inr_cr,
    ebitda_inr_cr,
    pat_inr_cr,
    dividend_declared_inr_cr,
    dividend_received_by_ongc_inr_cr
FROM subsidiary_financials
WHERE fiscal_year IN ('FY26', '2026')
ORDER BY pat_inr_cr DESC;
