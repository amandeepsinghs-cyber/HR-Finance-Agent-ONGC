-- Probe ID: W3.why
-- Parent ID: W3
-- Answer Type: what_if_sim
-- Question: Why does shifting senior technical officers from corporate headquarters directly improve field maintenance and facility uptime?
-- Personas: CMD
-- Tables: production_monthly, sanctioned_posts
-- Drill Dims: 
-- Story IDs: S31
-- Expected Output: list
-- Handcrafted: true

SELECT
    wc.city,
    COUNT(DISTINCT p.emp_id) AS current_delhi_deh_executives
FROM posting_history p
JOIN dim_work_centre wc ON p.wc_id = wc.wc_id
WHERE wc.wc_id IN ('WC-DEL', 'WC-DDN')
  AND p.to_date IS NULL
  AND p.grade_id LIKE 'E%'
GROUP BY wc.city;
