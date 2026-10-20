-- Probe ID: M1.compare_or_so_what
-- Parent ID: M1
-- Answer Type: sql
-- Question: How does the total workforce in Western Onshore assets compare with Eastern Offshore installations?
-- Personas: E1–E4 Officer (HR)
-- Tables: headcount_snapshot, dim_work_centre
-- Drill Dims: dim_work_centre.sector
-- Story IDs: S3
-- Expected Output: chart
-- Handcrafted: true

SELECT
    wc.sector,
    ROUND((SUM(CASE WHEN h.fiscal_year IN ('FY26', '2026') THEN h.headcount ELSE 0 END) -
           SUM(CASE WHEN h.fiscal_year IN ('FY21', '2021') THEN h.headcount ELSE 0 END)) * 100.0 /
          NULLIF(SUM(CASE WHEN h.fiscal_year IN ('FY21', '2021') THEN h.headcount ELSE 0 END), 0), 2) AS hc_growth_pct
FROM headcount_snapshot h
JOIN dim_work_centre wc ON h.wc_id = wc.wc_id
WHERE wc.sector IN ('Western', 'Eastern')
  AND h.fiscal_year IN ('FY21', '2021', 'FY26', '2026')
GROUP BY wc.sector;
