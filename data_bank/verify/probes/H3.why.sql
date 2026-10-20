-- Probe ID: H3.why
-- Parent ID: H3
-- Answer Type: sql_plus_rag
-- Question: Why is there a persistent vacancy gap in North-East and deepwater asset operational roles?
-- Personas: Director (HR)
-- Tables: sanctioned_posts, dim_work_centre
-- Drill Dims: dim_work_centre.hard_station_cat
-- Story IDs: S35
-- Expected Output: table
-- Handcrafted: false

SELECT
    dim_work_centre.hard_station_cat,
    SUM(sanctioned_posts.vacancy_count) AS metric_1
FROM sanctioned_posts
LEFT JOIN dim_work_centre ON sanctioned_posts.wc_id = dim_work_centre.wc_id
WHERE dim_work_centre.sector = 'NE'
GROUP BY dim_work_centre.hard_station_cat
ORDER BY dim_work_centre.hard_station_cat
LIMIT 100;
