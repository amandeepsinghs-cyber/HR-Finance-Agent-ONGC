-- Answer Key Follow-up SQL: C7__drill_down
-- Question: What is the cumulative 5-year capex allocation across Western Offshore (MH, B&S) versus Eastern Offshore (KG Basin)?
-- Type: data
-- Semantic audit 2026-10-20: old SQL listed actual capex by every work centre x FY (155 rows, institutes and
-- plants included) and never grouped Western vs Eastern Offshore. Now: FY22-FY26 actual capex (capex_budget,
-- 12 months per FY) for Western Offshore = Mumbai High (WC-MUM) + Bassein & Satellite (WC-BAS) and Eastern
-- Offshore = Eastern Offshore Asset (WC-EAS, KG-DWN-98/2), by year and cumulative, with share of company capex.

WITH c AS (
    SELECT
        CASE WHEN asset_wc_id IN ('WC-MUM', 'WC-BAS') THEN 'Western Offshore (MH, B&S)'
             WHEN asset_wc_id = 'WC-EAS' THEN 'Eastern Offshore (KG Basin)' END AS region,
        fiscal_year,
        actual_spend_inr_cr
    FROM capex_budget
    WHERE fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
),
tot AS (SELECT SUM(actual_spend_inr_cr) AS company_5yr FROM c)
SELECT
    region,
    ROUND(SUM(IF(fiscal_year = 'FY22', actual_spend_inr_cr, 0)), 0) AS fy22_cr,
    ROUND(SUM(IF(fiscal_year = 'FY23', actual_spend_inr_cr, 0)), 0) AS fy23_cr,
    ROUND(SUM(IF(fiscal_year = 'FY24', actual_spend_inr_cr, 0)), 0) AS fy24_cr,
    ROUND(SUM(IF(fiscal_year = 'FY25', actual_spend_inr_cr, 0)), 0) AS fy25_cr,
    ROUND(SUM(IF(fiscal_year = 'FY26', actual_spend_inr_cr, 0)), 0) AS fy26_cr,
    ROUND(SUM(actual_spend_inr_cr), 0) AS cumulative_5yr_cr,
    ROUND(SUM(actual_spend_inr_cr) * 100.0 / ANY_VALUE(tot.company_5yr), 1) AS pct_of_company_5yr_capex
FROM c CROSS JOIN tot
WHERE region IS NOT NULL
GROUP BY region
ORDER BY cumulative_5yr_cr DESC;
