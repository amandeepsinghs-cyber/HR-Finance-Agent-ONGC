-- Probe ID: C2
-- Parent ID: None
-- Answer Type: sql_plus_rag
-- Question: Who is overdue for transfer under the rotation policy, and which hard or remote stations (NE, offshore) are short of people to receive them?
-- Personas: CMD
-- Tables: posting_history, employee_master, sanctioned_posts, dim_work_centre
-- Drill Dims: dim_work_centre.wc_id, dim_work_centre.hard_station_cat
-- Story IDs: S2
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 2120.0 (ne_executive_manpower_norm)
-- Expected Range: 1908.0 - 2332.0 (tolerance: ±10.0%)

SELECT
    wc.wc_id,
    wc.hard_station_cat,
    wc.short_name,
    COUNT(DISTINCT e.emp_id) AS in_position_executives
FROM employee_master e
JOIN dim_work_centre wc ON e.current_wc_id = wc.wc_id
WHERE wc.wc_id IN ('WC-ASM', 'WC-JOR', 'WC-TRI', 'WC-SIL')
  AND e.current_grade_id LIKE 'E%'
  AND (e.employment_status = 'Active' OR e.separation_date IS NULL)
GROUP BY wc.wc_id, wc.hard_station_cat, wc.short_name
ORDER BY in_position_executives DESC;
