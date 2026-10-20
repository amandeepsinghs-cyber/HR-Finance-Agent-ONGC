-- Answer Key Follow-up SQL: F8__drill_down
-- Question: What is the 3-year trailing finding cost ($/BOE) in deepwater Western Offshore versus Krishna-Godavari and Assam-Arakan basins?
-- Type: data
-- Semantic audit 2026-10-20: used FY26 only although the question asks for a 3-year trailing figure. Now FY24-FY26
-- Semantic audit 2026-10-20: accretion-weighted finding cost per basin, with each year's value and the 3-year accretion.
-- Semantic audit 2026-10-20: Note: wells_drilled classifies Western Offshore as shallow_offshore; KG is the deepwater basin.

SELECT
    basin_name,
    ROUND(SUM(finding_cost_usd_per_boe * gross_reserves_accretion_mmtoe) / SUM(gross_reserves_accretion_mmtoe), 2) AS trailing_3yr_finding_cost_usd_boe,
    ROUND(SUM(IF(fiscal_year = 'FY24', finding_cost_usd_per_boe * gross_reserves_accretion_mmtoe, 0))
          / NULLIF(SUM(IF(fiscal_year = 'FY24', gross_reserves_accretion_mmtoe, 0)), 0), 2) AS fc_fy24_usd_boe,
    ROUND(SUM(IF(fiscal_year = 'FY25', finding_cost_usd_per_boe * gross_reserves_accretion_mmtoe, 0))
          / NULLIF(SUM(IF(fiscal_year = 'FY25', gross_reserves_accretion_mmtoe, 0)), 0), 2) AS fc_fy25_usd_boe,
    ROUND(SUM(IF(fiscal_year = 'FY26', finding_cost_usd_per_boe * gross_reserves_accretion_mmtoe, 0))
          / NULLIF(SUM(IF(fiscal_year = 'FY26', gross_reserves_accretion_mmtoe, 0)), 0), 2) AS fc_fy26_usd_boe,
    ROUND(SUM(gross_reserves_accretion_mmtoe), 2) AS accretion_3yr_mmtoe
FROM reserves_annual
WHERE basin_name IN ('Western Offshore', 'Krishna Godavari', 'Assam Arakan')
  AND fiscal_year IN ('FY24', 'FY25', 'FY26')
GROUP BY basin_name
ORDER BY trailing_3yr_finding_cost_usd_boe DESC;
