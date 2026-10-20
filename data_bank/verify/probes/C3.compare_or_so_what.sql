-- Probe ID: C3.compare_or_so_what
-- Parent ID: C3
-- Answer Type: sql
-- Question: How does the asset-wise headcount growth compare with the 5-year oil and gas production growth rate across those same assets?
-- Personas: CMD
-- Tables: headcount_snapshot, production_monthly, dim_work_centre
-- Drill Dims: dim_work_centre.name
-- Story IDs: S3
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc.short_name,
    ROUND((SUM(CASE WHEN h.fiscal_year IN ('FY26', '2026') THEN h.headcount ELSE 0 END) -
           SUM(CASE WHEN h.fiscal_year IN ('FY21', '2021') THEN h.headcount ELSE 0 END)) * 100.0 /
          NULLIF(SUM(CASE WHEN h.fiscal_year IN ('FY21', '2021') THEN h.headcount ELSE 0 END), 0), 2) AS hc_growth_pct
FROM headcount_snapshot h
JOIN dim_work_centre wc ON h.wc_id = wc.wc_id
WHERE wc.wc_id IN ('WC-EAS', 'WC-MEH')
  AND h.fiscal_year IN ('FY21', '2021', 'FY26', '2026')
GROUP BY wc.short_name;
