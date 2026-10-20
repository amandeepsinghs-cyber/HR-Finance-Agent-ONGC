-- Probe ID: H3.compare_or_so_what
-- Parent ID: H3
-- Answer Type: sql
-- Question: How does the executive vacancy rate in Assam Asset compare with Western Onshore assets (Mehsana, Ahmedabad)?
-- Personas: Director (HR)
-- Tables: sanctioned_posts, dim_work_centre
-- Drill Dims: dim_work_centre.short_name
-- Story IDs: S35
-- Expected Output: chart
-- Handcrafted: false

SELECT
    dim_work_centre.short_name,
    SUM(sanctioned_posts.vacancy_count) * 100.0 / NULLIF(SUM(sanctioned_posts.sanctioned_strength), 0) AS metric_1
FROM sanctioned_posts
LEFT JOIN dim_work_centre ON sanctioned_posts.wc_id = dim_work_centre.wc_id
WHERE dim_work_centre.short_name IN ('Assam Asset', 'Mehsana Asset', 'Ahmedabad Asset')
GROUP BY dim_work_centre.short_name
ORDER BY dim_work_centre.short_name
LIMIT 100;
