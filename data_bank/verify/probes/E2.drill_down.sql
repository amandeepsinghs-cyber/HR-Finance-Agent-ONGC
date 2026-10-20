-- Probe ID: E2.drill_down
-- Parent ID: E2
-- Answer Type: sql
-- Question: How many years of cumulative tenure have I completed at my current work centre and station cluster?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: posting_history, dim_work_centre
-- Drill Dims: dim_work_centre.cluster_id
-- Story IDs: S38
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc.cluster_id,
    ROUND(SUM(datediff('month', p.from_date, COALESCE(p.to_date, DATE '2026-10-19'))) / 12.0, 1) AS cumulative_tenure_years
FROM posting_history p
JOIN dim_work_centre wc ON p.wc_id = wc.wc_id
WHERE p.emp_id = 'EMP-102451'
GROUP BY wc.cluster_id;
