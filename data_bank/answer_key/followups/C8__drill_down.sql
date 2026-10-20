-- Answer Key Follow-up SQL: C8__drill_down
-- Question: Which specific fields in Assam and Cambay have sustained negative EBITDA for 3 consecutive fiscal years?
-- Type: data
-- Semantic audit 2026-10-20: old SQL listed FY24-FY26 rows for WC-ASM / WC-CAM without testing EBITDA < 0 and
-- left out Jorhat Asset (also in Assam, home of the FY26 loss-maker). Now one row per field in Assam Asset,
-- Jorhat Asset and Cambay Asset with FY24/FY25/FY26 EBITDA, the count of negative-EBITDA years and a flag for
-- "negative in all three"; an empty qualifying set is therefore explicit.

SELECT
    wc.short_name AS asset,
    f.name AS field_name,
    MAX(IF(pnl.fiscal_year = 'FY24', pnl.ebitda_inr_cr, NULL)) AS ebitda_fy24,
    MAX(IF(pnl.fiscal_year = 'FY25', pnl.ebitda_inr_cr, NULL)) AS ebitda_fy25,
    MAX(IF(pnl.fiscal_year = 'FY26', pnl.ebitda_inr_cr, NULL)) AS ebitda_fy26,
    COUNTIF(pnl.ebitda_inr_cr < 0) AS negative_ebitda_years,
    COUNTIF(pnl.ebitda_inr_cr < 0) = 3 AS negative_3_consecutive_years,
    MIN(pnl.ebitda_inr_cr) AS min_ebitda_fy24_fy26
FROM field_pnl_annual pnl
JOIN dim_field f ON pnl.field_id = f.field_id
JOIN dim_work_centre wc ON pnl.asset_wc_id = wc.wc_id
WHERE pnl.asset_wc_id IN ('WC-ASM', 'WC-JOR', 'WC-CAM')
  AND LOWER(pnl.line_type) = 'field'
  AND pnl.fiscal_year IN ('FY24', 'FY25', 'FY26')
GROUP BY wc.short_name, f.name
ORDER BY negative_ebitda_years DESC, min_ebitda_fy24_fy26 ASC;
