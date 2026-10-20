-- Probe ID: D5.drill_down
-- Parent ID: D5
-- Answer Type: sql
-- Question: What is the aggregate number of employees currently stationed at Delhi Corporate HQ?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: headcount_snapshot, dim_work_centre
-- Drill Dims: dim_work_centre.city
-- Story IDs: 
-- Expected Output: number
-- Handcrafted: false

SELECT
    dim_work_centre.city,
    SUM(headcount_snapshot.headcount) AS metric_1
FROM headcount_snapshot
LEFT JOIN dim_work_centre ON headcount_snapshot.wc_id = dim_work_centre.wc_id
WHERE dim_work_centre.city = 'New Delhi' AND headcount_snapshot.fiscal_year IN ('FY26', '2026')
GROUP BY dim_work_centre.city
ORDER BY dim_work_centre.city
LIMIT 100;
