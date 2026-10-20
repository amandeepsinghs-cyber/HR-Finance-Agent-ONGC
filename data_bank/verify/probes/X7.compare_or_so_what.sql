-- Probe ID: X7.compare_or_so_what
-- Parent ID: X7
-- Answer Type: sql
-- Question: How does the vacancy percentage in North-East work centres compare with ONGC's national average vacancy level?
-- Personas: CMD, Director (HR)
-- Tables: sanctioned_posts, dim_work_centre
-- Drill Dims: dim_work_centre.hard_station_cat
-- Story IDs: S35
-- Expected Output: table
-- Handcrafted: true

SELECT
    wc.hard_station_cat,
    SUM(sp.vacancy_count) AS formal_vacancies
FROM sanctioned_posts sp
JOIN dim_work_centre wc ON sp.wc_id = wc.wc_id
GROUP BY wc.hard_station_cat
ORDER BY wc.hard_station_cat;
