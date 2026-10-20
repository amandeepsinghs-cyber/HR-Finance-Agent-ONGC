-- Probe ID: M1.drill_down
-- Parent ID: M1
-- Answer Type: sql
-- Question: What is the breakdown of total headcount by executive versus non-executive cadre across assets?
-- Personas: E1–E4 Officer (HR)
-- Tables: headcount_snapshot, dim_work_centre, dim_grade
-- Drill Dims: dim_work_centre.name, dim_grade.cadre
-- Story IDs: S3
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc.name,
    g.cadre,
    SUM(h.headcount) AS total_headcount
FROM headcount_snapshot h
JOIN dim_work_centre wc ON h.wc_id = wc.wc_id
JOIN dim_grade g ON h.grade_id = g.grade_id
WHERE h.fiscal_year IN ('FY26', '2026')
GROUP BY wc.name, g.cadre
ORDER BY wc.name, g.cadre;
