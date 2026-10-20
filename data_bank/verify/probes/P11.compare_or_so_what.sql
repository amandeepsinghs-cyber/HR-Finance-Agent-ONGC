-- Probe ID: P11.compare_or_so_what
-- Parent ID: P11
-- Answer Type: sql
-- Question: What would be the net change in Delhi office staffing if all non-exempt tenure-breaching officers are rotated?
-- Personas: CMD, Director (HR)
-- Tables: posting_history, dim_work_centre
-- Drill Dims: 
-- Story IDs: S1
-- Expected Output: number
-- Handcrafted: true

SELECT
    wc.cluster_id,
    COUNT(DISTINCT p.emp_id) AS total_officers_ge_10yr
FROM posting_history p
JOIN dim_work_centre wc ON p.wc_id = wc.wc_id
WHERE wc.cluster_id IN ('CL-DEL', 'CL-MUM')
GROUP BY wc.cluster_id;
