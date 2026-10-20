-- Probe ID: X7
-- Parent ID: None
-- Answer Type: document_gen
-- Question: Generate a brief for the Parliamentary Committee on North-East executive vacancies and special recruitment drives.
-- Personas: CMD, Director (HR)
-- Tables: sanctioned_posts, dim_work_centre
-- Drill Dims: dim_work_centre.wc_id
-- Story IDs: S35
-- Expected Output: document
-- Handcrafted: true
-- Story Target: 1929.0 (ne_executive_manpower_norm_deficit)
-- Expected Range: 1736.1 - 2121.9 (tolerance: ±10.0%)

SELECT
    wc.wc_id,
    wc.short_name,
    SUM(sp.vacancy_count) AS total_vacancies,
    SUM(sp.special_drive_target_vacancies) AS special_drive_vacancies
FROM sanctioned_posts sp
JOIN dim_work_centre wc ON sp.wc_id = wc.wc_id
WHERE wc.sector = 'NE'
GROUP BY wc.wc_id, wc.short_name
ORDER BY total_vacancies DESC;
