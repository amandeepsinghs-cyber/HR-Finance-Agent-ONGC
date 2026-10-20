-- Probe ID: C8.drill_down
-- Parent ID: C8
-- Answer Type: sql
-- Question: Which specific fields in Assam and Cambay have sustained negative EBITDA for 3 consecutive fiscal years?
-- Personas: CMD
-- Tables: field_pnl_annual, dim_field, dim_work_centre
-- Drill Dims: dim_field.name, field_pnl_annual.fiscal_year
-- Story IDs: S6
-- Expected Output: table
-- Handcrafted: true

SELECT
    f.name AS field_name,
    pnl.fiscal_year,
    pnl.ebitda_inr_cr,
    pnl.pbt_inr_cr
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
WHERE wc.wc_id IN ('WC-ASM', 'WC-CAM')
  AND pnl.fiscal_year IN ('FY24', 'FY25', 'FY26')
ORDER BY f.name, pnl.fiscal_year;
