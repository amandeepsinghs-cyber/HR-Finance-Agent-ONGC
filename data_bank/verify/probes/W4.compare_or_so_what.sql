-- Probe ID: W4.compare_or_so_what
-- Parent ID: W4
-- Answer Type: sql
-- Question: How does the post-windfall tax realization compare with historical net realizations during peak oil price cycles?
-- Personas: Director (Finance)
-- Tables: price_fx_monthly
-- Drill Dims: price_fx_monthly.fiscal_year
-- Story IDs: S21
-- Expected Output: chart
-- Handcrafted: true

SELECT
    fiscal_year,
    ROUND(AVG(ongc_crude_net_realisation_usd_bbl), 2) AS avg_crude_realisation_usd_bbl
FROM price_fx_monthly
WHERE fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26', '2022', '2023', '2024', '2025', '2026')
GROUP BY fiscal_year
ORDER BY fiscal_year;
