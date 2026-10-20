-- Probe ID: C3
-- Parent ID: None
-- Answer Type: sql
-- Question: Which areas saw no headcount increase in the last 5 years, and which saw the most?
-- Personas: CMD
-- Tables: headcount_snapshot, dim_work_centre
-- Drill Dims: dim_work_centre.name
-- Story IDs: S3
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 620.0 (eastern_offshore_hc_fy21)
-- Expected Range: 558.0 - 682.0 (tolerance: ±10.0%)

SELECT
    wc.short_name,
    SUM(CASE WHEN h.fiscal_year IN ('FY21', '2021') THEN h.headcount ELSE 0 END) AS hc_fy21,
    SUM(CASE WHEN h.fiscal_year IN ('FY26', '2026') THEN h.headcount ELSE 0 END) AS hc_fy26,
    ROUND((SUM(CASE WHEN h.fiscal_year IN ('FY26', '2026') THEN h.headcount ELSE 0 END) -
           SUM(CASE WHEN h.fiscal_year IN ('FY21', '2021') THEN h.headcount ELSE 0 END)) * 100.0 /
          NULLIF(SUM(CASE WHEN h.fiscal_year IN ('FY21', '2021') THEN h.headcount ELSE 0 END), 0), 2) AS growth_pct
FROM headcount_snapshot h
JOIN dim_work_centre wc ON h.wc_id = wc.wc_id
WHERE wc.wc_id IN ('WC-EAS', 'WC-RAJ', 'WC-MEH', 'WC-CAM')
  AND h.fiscal_year IN ('FY21', '2021', 'FY26', '2026')
GROUP BY wc.short_name
ORDER BY growth_pct DESC;
