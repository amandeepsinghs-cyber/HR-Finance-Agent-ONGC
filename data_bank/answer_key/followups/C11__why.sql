-- Answer Key Follow-up SQL: C11__why
-- Question: Why did surface engineering and administrative staffing expand despite continuous reservoir pressure and production declines?
-- Type: data
-- Semantic audit 2026-10-20: old SQL SUMmed 12 monthly FY26 snapshots for Cambay only (a stock summed over
-- months) and had no earlier period, so "expand" could not be tested. The corrected parent (C11) finds no
-- asset that added headcount while losing production. Now: the 14 producing assets whose FY26 BOE is below
-- FY21, period-end headcount 31-Mar-2021 vs 31-Mar-2026 by discipline group (surface engineering /
-- administrative & support / subsurface, drilling & production / other technical), with each group's share of
-- the total in both years - testing whether these groups grew in absolute terms or only in share.

WITH declining AS (
    SELECT asset_wc_id AS wc_id
    FROM production_monthly
    WHERE fiscal_year IN ('FY21', 'FY26')
    GROUP BY asset_wc_id
    HAVING SUM(IF(fiscal_year = 'FY26', total_production_boe, 0)) < SUM(IF(fiscal_year = 'FY21', total_production_boe, 0))
),
h AS (
    SELECT
        CASE
            WHEN hs.discipline_id IN ('DISC-MEC', 'DISC-ELE', 'DISC-INS', 'DISC-CIV', 'DISC-AUT', 'DISC-TEL', 'DISC-IE') THEN 'Surface engineering'
            WHEN LOWER(d.function) IN ('support', 'finance', 'hr') THEN 'Administrative & support'
            WHEN hs.discipline_id IN ('DISC-DRL', 'DISC-PRD', 'DISC-RES', 'DISC-GEO', 'DISC-GPS', 'DISC-GPW', 'DISC-WEL') THEN 'Subsurface, drilling & production'
            ELSE 'Other technical'
        END AS discipline_group,
        SUM(IF(hs.month = '2021-03', hs.headcount, 0)) AS hc_mar21,
        SUM(IF(hs.month = '2026-03', hs.headcount, 0)) AS hc_mar26
    FROM headcount_snapshot hs
    JOIN declining dc ON dc.wc_id = hs.wc_id
    JOIN dim_discipline d ON d.discipline_id = hs.discipline_id
    WHERE hs.month IN ('2021-03', '2026-03')
    GROUP BY 1
)
SELECT
    discipline_group,
    hc_mar21,
    hc_mar26,
    hc_mar26 - hc_mar21 AS hc_change,
    ROUND((hc_mar26 - hc_mar21) * 100.0 / NULLIF(hc_mar21, 0), 1) AS hc_change_pct,
    ROUND(hc_mar21 * 100.0 / SUM(hc_mar21) OVER (), 1) AS share_mar21_pct,
    ROUND(hc_mar26 * 100.0 / SUM(hc_mar26) OVER (), 1) AS share_mar26_pct,
    (SELECT COUNT(*) FROM declining) AS declining_assets
FROM h
ORDER BY hc_change_pct DESC;
