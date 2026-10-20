-- Probe ID: C2.why
-- Parent ID: C2
-- Answer Type: sql_plus_rag
-- Question: Why have previous annual transfer cycles left North-East work centres persistently below sanctioned executive strength?
-- Personas: CMD
-- Tables: posting_history, sanctioned_posts, dim_work_centre
-- Drill Dims: posting_history.exemption_tag
-- Story IDs: S2
-- Expected Output: table
-- Handcrafted: true

SELECT
    COALESCE(p.exemption_tag, 'Impending_Retirement') AS exemption_tag,
    COUNT(DISTINCT p.emp_id) AS exempt_count
FROM posting_history p
JOIN dim_work_centre wc ON p.wc_id = wc.wc_id
WHERE wc.sector = 'NE'
GROUP BY p.exemption_tag
ORDER BY exempt_count DESC;
