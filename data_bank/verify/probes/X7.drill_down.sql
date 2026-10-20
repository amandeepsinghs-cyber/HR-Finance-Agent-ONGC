-- Probe ID: X7.drill_down
-- Parent ID: X7
-- Answer Type: sql
-- Question: What are the exact sanctioned versus in-position numbers in Assam and Tripura broken down by SC, ST, OBC, EWS, and General?
-- Personas: CMD, Director (HR)
-- Tables: sanctioned_posts, dim_work_centre
-- Drill Dims: dim_work_centre.state, sanctioned_posts.social_category
-- Story IDs: S35
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc.state,
    sp.social_category,
    SUM(sp.sanctioned_strength) AS sanctioned,
    SUM(sp.in_position_strength) AS in_position,
    SUM(sp.vacancy_count) AS formal_vacancies
FROM sanctioned_posts sp
JOIN dim_work_centre wc ON sp.wc_id = wc.wc_id
WHERE sp.wc_id IN ('WC-ASM', 'WC-TRI')
GROUP BY wc.state, sp.social_category
ORDER BY wc.state, sp.social_category;
