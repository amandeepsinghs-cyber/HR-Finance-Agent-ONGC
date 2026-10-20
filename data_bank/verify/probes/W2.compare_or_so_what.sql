-- Probe ID: W2.compare_or_so_what
-- Parent ID: W2
-- Answer Type: what_if_sim
-- Question: How would a hiring freeze impact our statutory reservation rosters and succession bench strength by FY28?
-- Personas: CMD, Director (HR)
-- Tables: sanctioned_posts, employee_master
-- Drill Dims: sanctioned_posts.social_category
-- Story IDs: S5
-- Expected Output: table
-- Handcrafted: false

SELECT
    sanctioned_posts.social_category,
    SUM(sanctioned_posts.backlog_vacancies) AS metric_1
FROM sanctioned_posts
LEFT JOIN employee_master ON employee_master.discipline_id = sanctioned_posts.discipline_id
WHERE datediff('year', employee_master.dob, DATE '2028-03-31') >= 60
GROUP BY sanctioned_posts.social_category
ORDER BY sanctioned_posts.social_category
LIMIT 100;
