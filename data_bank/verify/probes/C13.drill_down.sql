-- Probe ID: C13.drill_down
-- Parent ID: C13
-- Answer Type: what_if_sim
-- Question: Which field assets (e.g. Assam, Tripura, Karaikal) would gain the most production and maintenance engineering coverage?
-- Personas: CMD
-- Tables: sanctioned_posts, dim_work_centre, posting_history
-- Drill Dims: dim_work_centre.short_name
-- Story IDs: S31
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc.short_name,
    COUNT(DISTINCT p.emp_id) AS current_executives
FROM posting_history p
JOIN dim_work_centre wc ON p.wc_id = wc.wc_id
WHERE wc.wc_id IN ('WC-ASM', 'WC-TRI', 'WC-CAU')
  AND p.to_date IS NULL
  AND p.grade_id LIKE 'E%'
GROUP BY wc.short_name
ORDER BY wc.short_name;
