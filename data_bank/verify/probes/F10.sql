-- Probe ID: F10
-- Parent ID: None
-- Answer Type: document_gen
-- Question: Generate a quarterly asset-wise P&L sheet.
-- Personas: Director (Finance)
-- Tables: field_pnl_annual, production_monthly, cost_ledger, dim_work_centre
-- Drill Dims: dim_work_centre.name
-- Story IDs: S6
-- Expected Output: document
-- Handcrafted: true
-- Story Target: 0.042 (borholla_oil_production_mmt)
-- Expected Range: 0.04 - 0.05 (tolerance: ±10.0%)

SELECT
    wc.name AS work_centre_name,
    pnl.fiscal_year,
    SUM(pnl.gross_revenue_inr_cr) AS total_gross_revenue_cr,
    SUM(pnl.total_opex_inr_cr) AS total_opex_cr,
    SUM(pnl.ebitda_inr_cr) AS total_ebitda_cr,
    SUM(pnl.pbt_inr_cr) AS total_pbt_cr
FROM field_pnl_annual pnl
JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
WHERE pnl.fiscal_year IN ('FY26', '2026')
GROUP BY wc.name, pnl.fiscal_year
ORDER BY total_pbt_cr DESC;
