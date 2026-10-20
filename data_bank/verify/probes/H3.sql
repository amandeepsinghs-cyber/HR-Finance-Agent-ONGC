-- Probe ID: H3
-- Parent ID: None
-- Answer Type: sql
-- Question: What is the vacancy position (sanctioned vs. in-position) by asset and discipline?
-- Personas: Director (HR)
-- Tables: sanctioned_posts, dim_work_centre, dim_discipline
-- Drill Dims: dim_work_centre.name, dim_discipline.name
-- Story IDs: S35
-- Expected Output: table
-- Handcrafted: false
-- Story Target: 30.0 (assam_formal_total_vacancies)
-- Expected Range: 27.0 - 33.0 (tolerance: ±10.0%)

SELECT
    dim_work_centre.name,
    dim_discipline.name,
    SUM(sanctioned_posts.vacancy_count) AS metric_1,
    AVG(sanctioned_posts.vacancy_rate_pct) AS metric_2
FROM sanctioned_posts
LEFT JOIN dim_work_centre ON sanctioned_posts.wc_id = dim_work_centre.wc_id
LEFT JOIN dim_discipline ON sanctioned_posts.discipline_id = dim_discipline.discipline_id
WHERE sanctioned_posts.fiscal_year IN ('FY26', '2026')
GROUP BY dim_work_centre.name, dim_discipline.name
ORDER BY dim_work_centre.name
LIMIT 100;
