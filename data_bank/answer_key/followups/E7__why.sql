-- Answer Key Follow-up SQL: E7__why
-- Question: What major factors (crude realization, statutory cess, dividend income) drove the annual profit growth?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL returned revenue minus levies mislabelled as statutory_levies_total (106,509) - not a driver analysis; profit actually FELL.
-- Semantic audit 2026-10-20: Now FY25->FY26 bridge: Brent, realisation, FX, revenue, levies (royalty/cess/windfall), opex, employee cost, EBITDA, DD&A, PBT, PAT. Dividend income not in data (GAP).

WITH cf AS (
    SELECT fiscal_year,
           CAST(gross_revenue_inr_cr AS FLOAT64) AS gross_revenue_inr_cr,
           CAST(statutory_levies_total_inr_cr AS FLOAT64) AS statutory_levies_inr_cr,
           CAST(royalty_inr_cr AS FLOAT64) AS royalty_inr_cr,
           CAST(oidb_cess_inr_cr AS FLOAT64) AS oidb_cess_inr_cr,
           CAST(saed_windfall_tax_inr_cr AS FLOAT64) AS windfall_tax_inr_cr,
           CAST(operating_expenses_total_inr_cr AS FLOAT64) AS operating_expenses_inr_cr,
           CAST(employee_cost_total_inr_cr AS FLOAT64) AS employee_cost_inr_cr,
           CAST(ebitda_inr_cr AS FLOAT64) AS ebitda_inr_cr,
           CAST(dda_inr_cr AS FLOAT64) AS dda_inr_cr,
           CAST(pbt_inr_cr AS FLOAT64) AS pbt_inr_cr,
           CAST(pat_inr_cr AS FLOAT64) AS pat_inr_cr
    FROM corporate_financials
    WHERE fiscal_year IN ('FY25', 'FY26')
),
px AS (
    SELECT fiscal_year,
           CAST(AVG(brent_usd_bbl) AS FLOAT64) AS brent_usd_bbl,
           CAST(AVG(ongc_crude_net_realisation_usd_bbl) AS FLOAT64) AS crude_realisation_usd_bbl,
           CAST(AVG(inr_usd_fx_rate) AS FLOAT64) AS inr_usd_fx
    FROM price_fx_monthly
    WHERE fiscal_year IN ('FY25', 'FY26')
    GROUP BY fiscal_year
),
u AS (
    SELECT fiscal_year, metric, value
    FROM (SELECT * FROM cf JOIN px USING (fiscal_year))
    UNPIVOT (value FOR metric IN (brent_usd_bbl, crude_realisation_usd_bbl, inr_usd_fx, gross_revenue_inr_cr,
                                  statutory_levies_inr_cr, royalty_inr_cr, oidb_cess_inr_cr, windfall_tax_inr_cr,
                                  operating_expenses_inr_cr, employee_cost_inr_cr, ebitda_inr_cr, dda_inr_cr,
                                  pbt_inr_cr, pat_inr_cr))
)
SELECT
    metric,
    ROUND(MAX(IF(fiscal_year = 'FY25', value, NULL)), 2) AS fy25,
    ROUND(MAX(IF(fiscal_year = 'FY26', value, NULL)), 2) AS fy26,
    ROUND(MAX(IF(fiscal_year = 'FY26', value, NULL)) - MAX(IF(fiscal_year = 'FY25', value, NULL)), 2) AS change
FROM u
GROUP BY metric
ORDER BY CASE metric
    WHEN 'brent_usd_bbl' THEN 1 WHEN 'crude_realisation_usd_bbl' THEN 2 WHEN 'inr_usd_fx' THEN 3
    WHEN 'gross_revenue_inr_cr' THEN 4 WHEN 'statutory_levies_inr_cr' THEN 5 WHEN 'royalty_inr_cr' THEN 6
    WHEN 'oidb_cess_inr_cr' THEN 7 WHEN 'windfall_tax_inr_cr' THEN 8 WHEN 'operating_expenses_inr_cr' THEN 9
    WHEN 'employee_cost_inr_cr' THEN 10 WHEN 'ebitda_inr_cr' THEN 11 WHEN 'dda_inr_cr' THEN 12
    WHEN 'pbt_inr_cr' THEN 13 ELSE 14 END;
