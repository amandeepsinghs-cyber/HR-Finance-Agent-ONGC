-- Probe ID: C3.drill_down
-- Parent ID: C3
-- Answer Type: sql
-- Question: Break down the 5-year headcount trajectory of Rajahmundry, Eastern Offshore, Mehsana, and Cambay by executive vs non-executive.
-- Personas: CMD
-- Tables: headcount_snapshot, dim_work_centre, dim_grade
-- Drill Dims: dim_work_centre.short_name, dim_grade.cadre, headcount_snapshot.fiscal_year
-- Story IDs: S3
-- Expected Output: chart
-- Handcrafted: true

SELECT
    wc.short_name,
    g.cadre,
    h.fiscal_year,
    SUM(h.headcount) AS total_headcount
FROM headcount_snapshot h
JOIN dim_work_centre wc ON h.wc_id = wc.wc_id
JOIN dim_grade g ON h.grade_id = g.grade_id
WHERE wc.wc_id IN ('WC-EAS', 'WC-RAJ', 'WC-MEH', 'WC-CAM')
  AND h.fiscal_year IN ('FY21', '2021', 'FY26', '2026')
GROUP BY wc.short_name, g.cadre, h.fiscal_year
ORDER BY wc.short_name, g.cadre, h.fiscal_year;
