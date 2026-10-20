-- Answer Key Follow-up SQL: F8__compare_or_so_what
-- Question: How does the annual Reserve Replacement Ratio (RRR 2P) across domestic basins compare against the target of >1.0?
-- Type: data
-- Semantic audit 2026-10-20: returned a single FY26 unweighted average. Now FY22-FY26 per year: company RRR = SUM(2P
-- Semantic audit 2026-10-20: accretion) / SUM(production), lowest and highest basin RRR, basins below 1.0, vs the 1.0 target.

WITH b AS (
    SELECT fiscal_year, basin_name,
           SUM(gross_reserves_accretion_mmtoe) / NULLIF(SUM(annual_production_mmtoe), 0) AS rrr,
           SUM(gross_reserves_accretion_mmtoe) AS acc,
           SUM(annual_production_mmtoe) AS prod
    FROM reserves_annual
    WHERE fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
    GROUP BY fiscal_year, basin_name
)
SELECT
    fiscal_year,
    ROUND(SUM(acc) / SUM(prod), 2) AS company_rrr_2p,
    1.0 AS target_rrr,
    ROUND(MIN(rrr), 2) AS min_basin_rrr,
    ARRAY_AGG(basin_name ORDER BY rrr ASC LIMIT 1)[OFFSET(0)] AS min_basin,
    ROUND(MAX(rrr), 2) AS max_basin_rrr,
    COUNTIF(rrr < 1.0) AS basins_below_target,
    COUNT(*) AS basins
FROM b
GROUP BY fiscal_year
ORDER BY fiscal_year;
