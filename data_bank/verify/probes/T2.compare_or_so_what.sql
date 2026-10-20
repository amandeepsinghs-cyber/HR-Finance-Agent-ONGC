-- Probe ID: T2.compare_or_so_what
-- Parent ID: T2
-- Answer Type: sql
-- Question: How does transferring these executives balance vacancy deficits in North-East assets while controlling transfer allowance expenses?
-- Personas: CMD, Director (HR)
-- Tables: sanctioned_posts, posting_history, dim_work_centre
-- Drill Dims: dim_work_centre.wc_id
-- Story IDs: S1
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc.wc_id,
    wc.sector,
    COUNT(DISTINCT p.emp_id) AS active_executives
FROM posting_history p
JOIN dim_work_centre wc ON p.wc_id = wc.wc_id
WHERE p.to_date IS NULL AND p.grade_id LIKE 'E%'
GROUP BY wc.wc_id, wc.sector
ORDER BY active_executives DESC;
