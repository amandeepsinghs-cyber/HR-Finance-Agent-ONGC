-- Probe ID: C11
-- Parent ID: None
-- Answer Type: sql
-- Question: Which assets added headcount but lost production over 5 years?
-- Personas: CMD
-- Tables: headcount_snapshot, production_monthly, field_pnl_annual, dim_work_centre
-- Drill Dims: dim_work_centre.name
-- Story IDs: S7
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 514.0 (cambay_headcount_fy21)
-- Expected Range: 462.6 - 565.4 (tolerance: ±10.0%)

WITH hc_diff AS (
    SELECT
        wc_id,
        SUM(CASE WHEN fiscal_year IN ('FY26', '2026') THEN headcount ELSE 0 END) AS hc_fy26,
        SUM(CASE WHEN fiscal_year IN ('FY21', '2021') THEN headcount ELSE 0 END) AS hc_fy21,
        ROUND((SUM(CASE WHEN fiscal_year IN ('FY26', '2026') THEN headcount ELSE 0 END) -
               SUM(CASE WHEN fiscal_year IN ('FY21', '2021') THEN headcount ELSE 0 END)) * 100.0 /
              NULLIF(SUM(CASE WHEN fiscal_year IN ('FY21', '2021') THEN headcount ELSE 0 END), 0), 2) AS hc_growth_pct
    FROM headcount_snapshot
    WHERE fiscal_year IN ('FY21', '2021', 'FY26', '2026')
    GROUP BY wc_id
),
prod_diff AS (
    SELECT
        asset_wc_id AS wc_id,
        ROUND(SUM(CASE WHEN fiscal_year IN ('FY26', '2026') THEN oil_production_mt/1e6 + gas_production_mmscm/1e3 ELSE 0 END), 3) AS prod_fy26,
        ROUND(SUM(CASE WHEN fiscal_year IN ('FY21', '2021') THEN oil_production_mt/1e6 + gas_production_mmscm/1e3 ELSE 0 END), 3) AS prod_fy21,
        ROUND((SUM(CASE WHEN fiscal_year IN ('FY26', '2026') THEN oil_production_mt/1e6 + gas_production_mmscm/1e3 ELSE 0 END) -
               SUM(CASE WHEN fiscal_year IN ('FY21', '2021') THEN oil_production_mt/1e6 + gas_production_mmscm/1e3 ELSE 0 END)) * 100.0 /
              NULLIF(SUM(CASE WHEN fiscal_year IN ('FY21', '2021') THEN oil_production_mt/1e6 + gas_production_mmscm/1e3 ELSE 0 END), 0), 2) AS prod_growth_pct
    FROM production_monthly
    WHERE fiscal_year IN ('FY21', '2021', 'FY26', '2026')
    GROUP BY asset_wc_id
)
SELECT
    wc.wc_id,
    wc.short_name,
    h.hc_fy21,
    h.hc_fy26,
    h.hc_growth_pct,
    p.prod_fy21,
    p.prod_fy26,
    p.prod_growth_pct
FROM hc_diff h
JOIN prod_diff p ON h.wc_id = p.wc_id
JOIN dim_work_centre wc ON h.wc_id = wc.wc_id
WHERE h.hc_growth_pct > 0 AND p.prod_growth_pct < 0
ORDER BY p.prod_growth_pct ASC;
