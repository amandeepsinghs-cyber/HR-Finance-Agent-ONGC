-- Probe ID: P12.compare_or_so_what
-- Parent ID: P12
-- Answer Type: sql
-- Question: How does the promotion clearance rate compare between officers who fulfilled the hardship criteria versus those with waivers?
-- Personas: Director (HR)
-- Tables: dpc_cases, employee_master, posting_history, dim_work_centre
-- Drill Dims: employee_master.has_hard_station_tenure, dpc_cases.status
-- Story IDs: S2
-- Expected Output: table
-- Handcrafted: true

-- Note: Hard station per JRTP hardship category is hard_station_cat = 'C'
WITH hard_station_officers AS (
    SELECT DISTINCT p.emp_id
    FROM posting_history p
    JOIN dim_work_centre wc ON p.wc_id = wc.wc_id
    WHERE wc.hard_station_cat = 'C'
)
SELECT
    CASE WHEN hs.emp_id IS NOT NULL THEN TRUE ELSE FALSE END AS has_hard_station_tenure,
    d.status,
    COUNT(DISTINCT d.emp_id) AS candidates_count
FROM dpc_cases d
LEFT JOIN hard_station_officers hs ON d.emp_id = hs.emp_id
GROUP BY 1, d.status
ORDER BY 1, d.status;
