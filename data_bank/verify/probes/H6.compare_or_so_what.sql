-- Probe ID: H6.compare_or_so_what
-- Parent ID: H6
-- Answer Type: sql_plus_rag
-- Question: How do our current roster representation percentages compare against statutory presidential directives and DoPT guidelines?
-- Personas: Director (HR)
-- Tables: sanctioned_posts
-- Drill Dims: sanctioned_posts.social_category
-- Story IDs: S16
-- Expected Output: table
-- Handcrafted: false

SELECT
    sanctioned_posts.social_category,
    SUM(sanctioned_posts.in_position_strength) * 100.0 / NULLIF(SUM(sanctioned_posts.sanctioned_strength), 0) AS metric_1
FROM sanctioned_posts
GROUP BY sanctioned_posts.social_category
ORDER BY sanctioned_posts.social_category
LIMIT 100;
