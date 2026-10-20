-- Probe ID: T1
-- Parent ID: None
-- Answer Type: document_gen
-- Question: "Which fields lost money in FY26?" → "Why is Field X losing?" → "How many people work there, and what do they cost?" → "Draft a board note with options."
-- Personas: CMD, Director (Finance)
-- Tables: field_pnl_annual, production_monthly, headcount_snapshot, payroll_monthly
-- Drill Dims: field_pnl_annual.field_id
-- Story IDs: S6
-- Expected Output: document
-- Handcrafted: true
-- Story Target: 0.042 (borholla_oil_production_mmt)
-- Expected Range: 0.04 - 0.05 (tolerance: ±10.0%)

SELECT
    pnl.field_id,
    f.name AS field_name,
    pnl.fiscal_year,
    pnl.gross_revenue_inr_cr,
    pnl.total_opex_inr_cr,
    pnl.ebitda_inr_cr,
    pnl.pbt_inr_cr
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
WHERE pnl.fiscal_year IN ('FY26', '2026')
  AND (pnl.pbt_inr_cr < 0 OR pnl.ebitda_inr_cr < 0)
ORDER BY pnl.pbt_inr_cr ASC;
