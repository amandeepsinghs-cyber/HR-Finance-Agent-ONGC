-- Probe ID: H6.drill_down
-- Parent ID: H6
-- Answer Type: sql
-- Question: What is the exact representation percentage and backlog vacancy count for SC, ST, OBC, EWS, and PwD in E1 to E7?
-- Personas: Director (HR)
-- Tables: sanctioned_posts
-- Drill Dims: sanctioned_posts.grade_id, sanctioned_posts.social_category
-- Story IDs: S16
-- Expected Output: table
-- Handcrafted: false

SELECT
    sanctioned_posts.grade_id,
    sanctioned_posts.social_category,
    SUM(sanctioned_posts.backlog_vacancies) AS metric_1
FROM sanctioned_posts
WHERE sanctioned_posts.grade_id IN ('E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7')
GROUP BY sanctioned_posts.grade_id, sanctioned_posts.social_category
ORDER BY sanctioned_posts.grade_id
LIMIT 100;
