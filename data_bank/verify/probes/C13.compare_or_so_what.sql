-- Probe ID: C13.compare_or_so_what
-- Parent ID: C13
-- Answer Type: what_if_sim
-- Question: How would the reduction in Delhi/Dehradun corporate overhead compare against improved field asset uptime and supervisor ratios?
-- Personas: CMD
-- Tables: payroll_monthly, dim_work_centre
-- Drill Dims: dim_work_centre.city
-- Story IDs: S31
-- Expected Output: table
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
