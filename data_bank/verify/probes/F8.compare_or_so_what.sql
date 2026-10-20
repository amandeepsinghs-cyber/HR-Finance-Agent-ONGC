-- Probe ID: F8.compare_or_so_what
-- Parent ID: F8
-- Answer Type: sql
-- Question: How does the annual Reserve Replacement Ratio (RRR 2P) across domestic basins compare against the target of >1.0?
-- Personas: Director (Finance)
-- Tables: reserves_annual
-- Drill Dims: reserves_annual.fiscal_year
-- Story IDs: S24
-- Expected Output: number
-- Handcrafted: true

SELECT
    r.fiscal_year,
    ROUND(AVG(r.reserve_replacement_ratio_rrr_2p), 2) AS avg_rrr_2p
FROM reserves_annual r
WHERE r.fiscal_year IN ('FY26', '2026')
GROUP BY r.fiscal_year;
