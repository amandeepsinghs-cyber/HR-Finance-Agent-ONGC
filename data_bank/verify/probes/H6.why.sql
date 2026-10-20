-- Probe ID: H6.why
-- Parent ID: H6
-- Answer Type: sql_plus_rag
-- Question: Why has backlog vacancy clearance lagged in specialized technical disciplines like Geoscience and Marine Engineering?
-- Personas: Director (HR)
-- Tables: sanctioned_posts, dim_discipline
-- Drill Dims: dim_discipline.name, sanctioned_posts.social_category
-- Story IDs: S16
-- Expected Output: table
-- Handcrafted: false

SELECT
    dim_discipline.name,
    sanctioned_posts.social_category,
    SUM(sanctioned_posts.backlog_vacancies) AS metric_1
FROM sanctioned_posts
LEFT JOIN dim_discipline ON sanctioned_posts.discipline_id = dim_discipline.discipline_id
WHERE dim_discipline.name IN ('Geology', 'Geophysics (Surface)', 'Marine / Naval Architecture')
GROUP BY dim_discipline.name, sanctioned_posts.social_category
ORDER BY dim_discipline.name
LIMIT 100;
