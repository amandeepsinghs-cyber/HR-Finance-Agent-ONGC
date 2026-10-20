-- Probe ID: H2.why
-- Parent ID: H2
-- Answer Type: sql_plus_rag
-- Question: Why have these executives been repeatedly posted across non-hard clusters (e.g. Delhi, Dehradun, Ahmedabad, Mumbai)?
-- Personas: Director (HR)
-- Tables: posting_history, dim_work_centre
-- Drill Dims: dim_work_centre.cluster_id
-- Story IDs: S2
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc.cluster_id,
    COUNT(DISTINCT p.emp_id) AS postings_count
FROM posting_history p
JOIN dim_work_centre wc ON p.wc_id = wc.wc_id
WHERE wc.sector = 'NE'
GROUP BY wc.cluster_id;
