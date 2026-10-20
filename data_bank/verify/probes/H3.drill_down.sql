-- Probe ID: H3.drill_down
-- Parent ID: H3
-- Answer Type: sql
-- Question: Which critical disciplines (Instrumentation, Petroleum, Chemical, Geophysics) have a vacancy deficit exceeding 15%?
-- Personas: Director (HR)
-- Tables: sanctioned_posts, dim_discipline
-- Drill Dims: dim_discipline.name
-- Story IDs: S35
-- Expected Output: table
-- Handcrafted: false

SELECT
    dim_discipline.name,
    SUM(sanctioned_posts.vacancy_count) * 100.0 / NULLIF(SUM(sanctioned_posts.sanctioned_strength), 0) AS metric_1
FROM sanctioned_posts
LEFT JOIN dim_discipline ON sanctioned_posts.discipline_id = dim_discipline.discipline_id
WHERE dim_discipline.name IN ('Instrumentation', 'Production', 'Chemistry', 'Geophysics (Surface)')
GROUP BY dim_discipline.name
ORDER BY dim_discipline.name
LIMIT 100;
