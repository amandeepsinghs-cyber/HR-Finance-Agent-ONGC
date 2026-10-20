-- Probe ID: X7.why
-- Parent ID: X7
-- Answer Type: sql
-- Question: What specific recruitment initiatives and special drives have been launched to fill reserved category vacancies in the North-East?
-- Personas: CMD, Director (HR)
-- Tables: sanctioned_posts
-- Drill Dims: sanctioned_posts.special_drive_name
-- Story IDs: S35
-- Expected Output: table
-- Handcrafted: true

SELECT
    special_drive_name,
    SUM(special_drive_target_vacancies) AS target_vacancies
FROM sanctioned_posts
WHERE special_drive_name IS NOT NULL
GROUP BY special_drive_name
ORDER BY target_vacancies DESC;
