-- Probe ID: C2.compare_or_so_what
-- Parent ID: C2
-- Answer Type: sql
-- Question: How many of the overdue executives have never completed a mandatory tenure in a Category-C or offshore location?
-- Personas: CMD
-- Tables: employee_master, posting_history, dim_work_centre
-- Drill Dims: employee_master.has_hard_station_tenure, employee_master.has_offshore_tenure
-- Story IDs: S2
-- Expected Output: table
-- Handcrafted: true

-- Note: Hard station per JRTP hardship category is hard_station_cat = 'C'
WITH hard_station AS (
    SELECT DISTINCT p.emp_id
    FROM posting_history p
    JOIN dim_work_centre wc ON p.wc_id = wc.wc_id
    WHERE wc.hard_station_cat = 'C'
),
offshore AS (
    SELECT DISTINCT p.emp_id
    FROM posting_history p
    JOIN dim_work_centre wc ON p.wc_id = wc.wc_id
    WHERE LOWER(wc.onshore_offshore) = 'offshore'
)
SELECT
    CASE WHEN hs.emp_id IS NOT NULL THEN TRUE ELSE FALSE END AS has_hard_station_tenure,
    CASE WHEN off.emp_id IS NOT NULL THEN TRUE ELSE FALSE END AS has_offshore_tenure,
    COUNT(DISTINCT e.emp_id) AS officer_count
FROM employee_master e
LEFT JOIN hard_station hs ON e.emp_id = hs.emp_id
LEFT JOIN offshore off ON e.emp_id = off.emp_id
WHERE e.current_grade_id IN ('E3', 'E4', 'E5')
  AND (e.employment_status = 'Active' OR e.separation_date IS NULL)
GROUP BY 1, 2
ORDER BY 1, 2;
