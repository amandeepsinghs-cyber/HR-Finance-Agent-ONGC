-- Probe ID: C14.why
-- Parent ID: C14
-- Answer Type: sql_plus_rag
-- Question: What specific reservoir recovery mechanism or operating constraint is identified as the root cause of loss in each field?
-- Personas: CMD
-- Tables: field_pnl_annual, dim_field
-- Drill Dims: dim_field.name, field_pnl_annual.root_cause_loss_code
-- Story IDs: S6
-- Expected Output: table
-- Handcrafted: true

SELECT
    f.name AS field_name,
    pnl.root_cause_loss_code,
    SUM(pnl.pbt_inr_cr) AS field_pbt_cr
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
WHERE pnl.fiscal_year IN ('FY26', '2026')
  AND pnl.root_cause_loss_code IS NOT NULL
GROUP BY f.name, pnl.root_cause_loss_code
ORDER BY field_pbt_cr ASC;
