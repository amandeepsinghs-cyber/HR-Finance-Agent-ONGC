-- Probe ID: C11.why
-- Parent ID: C11
-- Answer Type: sql
-- Question: Why did surface engineering and administrative staffing expand despite continuous reservoir pressure and production declines?
-- Personas: CMD
-- Tables: headcount_snapshot, dim_work_centre, dim_discipline
-- Drill Dims: dim_discipline.name
-- Story IDs: S7
-- Expected Output: table
-- Handcrafted: true

SELECT
    d.name,
    SUM(hs.headcount) AS staff_count
FROM headcount_snapshot hs
JOIN dim_discipline d ON hs.discipline_id = d.discipline_id
WHERE hs.wc_id = 'WC-CAM' AND hs.fiscal_year = 'FY26'
GROUP BY d.name
ORDER BY staff_count DESC;
