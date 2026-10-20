-- Probe ID: H7.drill_down
-- Parent ID: H7
-- Answer Type: sql
-- Question: How many women executives are currently deployed in rotational offshore shifts on Mumbai High platforms and rigs?
-- Personas: Director (HR)
-- Tables: posting_history, employee_master, dim_work_centre
-- Drill Dims: dim_work_centre.short_name
-- Story IDs: S17
-- Expected Output: number
-- Handcrafted: true

SELECT
    wc.short_name,
    COUNT(DISTINCT e.emp_id) AS female_offshore_count
FROM employee_master e
JOIN dim_work_centre wc ON e.current_wc_id = wc.wc_id
WHERE e.gender = 'Female'
  AND LOWER(wc.onshore_offshore) = 'offshore'
  AND (e.employment_status = 'Active' OR e.separation_date IS NULL)
GROUP BY wc.short_name;
