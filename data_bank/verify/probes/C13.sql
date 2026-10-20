-- Probe ID: C13
-- Parent ID: None
-- Answer Type: what_if_sim
-- Question: If we move 200 executives from Delhi/Dehradun to field assets, what changes in cost and coverage?
-- Personas: CMD
-- Tables: posting_history, payroll_monthly, sanctioned_posts, dim_work_centre
-- Drill Dims: dim_work_centre.wc_id
-- Story IDs: S31
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 200.0 (simulated_rebalanced_headcount)
-- Expected Range: 180.0 - 220.0 (tolerance: ±10.0%)

SELECT
    wc.wc_id,
    wc.city,
    COUNT(DISTINCT p.emp_id) AS current_delhi_deh_executives
FROM posting_history p
JOIN dim_work_centre wc ON p.wc_id = wc.wc_id
WHERE wc.wc_id IN ('WC-DEL', 'WC-DDN')
  AND p.to_date IS NULL
  AND p.grade_id LIKE 'E%'
GROUP BY wc.wc_id, wc.city;
