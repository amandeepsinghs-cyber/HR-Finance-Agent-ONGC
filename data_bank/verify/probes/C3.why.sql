-- Probe ID: C3.why
-- Parent ID: C3
-- Answer Type: sql_plus_rag
-- Question: What operational developments (e.g. KG-DWN-98/2 deepwater ramp-up vs mature field natural decline) drove this headcount shift?
-- Personas: CMD
-- Tables: production_monthly, project_progress, dim_work_centre
-- Drill Dims: dim_work_centre.wc_id, production_monthly.fiscal_year
-- Story IDs: S3
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc.short_name,
    p.fiscal_year,
    ROUND(SUM(p.oil_production_mt) / 1000.0, 2) AS oil_prod_kmt,
    ROUND(SUM(p.gas_production_mmscm), 2) AS gas_prod_mmscm
FROM production_monthly p
JOIN dim_work_centre wc ON p.asset_wc_id = wc.wc_id
WHERE wc.wc_id IN ('WC-EAS', 'WC-CAM')
  AND p.fiscal_year IN ('FY21', '2021', 'FY26', '2026')
GROUP BY wc.short_name, p.fiscal_year
ORDER BY wc.short_name, p.fiscal_year;
