-- Answer Key Follow-up SQL: X7__why
-- Question: What specific recruitment initiatives and special drives have been launched to fill reserved category vacancies in the North-East?
-- Type: document
-- Semantic audit 2026-10-20: Scoped to the North-East (old SQL reported the all-India special drive total of 179): special recruitment
-- drive targets and backlog reserved vacancies in NE work centres, with NE share of the national drive.
WITH nat AS (
    SELECT SUM(special_drive_target_vacancies) AS national_drive_target
    FROM sanctioned_posts WHERE special_drive_flag AND fiscal_year = 'FY26'
)
SELECT
    sp.special_drive_name,
    wc.short_name,
    sp.social_category AS category,
    SUM(sp.backlog_vacancies) AS backlog_reserved_vacancies,
    SUM(sp.special_drive_target_vacancies) AS special_drive_target,
    ANY_VALUE(nat.national_drive_target) AS national_drive_target
FROM sanctioned_posts sp
JOIN dim_work_centre wc ON sp.wc_id = wc.wc_id
CROSS JOIN nat
WHERE wc.sector = 'NE' AND sp.special_drive_flag AND sp.fiscal_year = 'FY26'
GROUP BY sp.special_drive_name, wc.short_name, sp.social_category
ORDER BY special_drive_target DESC, wc.short_name, category;
