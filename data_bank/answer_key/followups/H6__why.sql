-- Answer Key Follow-up SQL: H6__why
-- Question: Why has backlog vacancy clearance lagged in specialized technical disciplines like Geoscience and Marine Engineering?
-- Type: data
-- Semantic audit 2026-10-20: old SQL had no FY filter and no context (Marine / Naval Architecture has no sanctioned posts, so it
-- silently vanished). Now: FY26 backlog reserved vacancies, total category vacancies and sanctioned reserved posts for SC/ST in
-- Geology, Geophysics and Marine, each discipline's share of the company backlog, plus a company row.
WITH d AS (
    SELECT dd.name AS discipline, sp.*
    FROM sanctioned_posts sp
    JOIN dim_discipline dd ON dd.discipline_id = sp.discipline_id
    WHERE sp.fiscal_year = 'FY26' AND LOWER(sp.social_category) IN ('sc', 'st')
)
SELECT
    discipline,
    social_category,
    SUM(sanctioned_strength) AS reserved_sanctioned,
    SUM(vacancy_count) AS category_vacancies,
    SUM(backlog_vacancies) AS backlog_vacancies,
    ROUND(SUM(backlog_vacancies) * 100.0 / NULLIF(SUM(vacancy_count), 0), 1) AS backlog_pct_of_vacancies,
    ROUND(SUM(backlog_vacancies) * 100.0 / (SELECT SUM(backlog_vacancies) FROM d), 1) AS share_of_company_backlog_pct
FROM d
WHERE discipline IN ('Geology', 'Geophysics (Surface)', 'Geophysics (Wells)', 'Marine / Naval Architecture')
GROUP BY discipline, social_category
UNION ALL
SELECT 'All disciplines', social_category, SUM(sanctioned_strength), SUM(vacancy_count), SUM(backlog_vacancies),
       ROUND(SUM(backlog_vacancies) * 100.0 / NULLIF(SUM(vacancy_count), 0), 1),
       ROUND(SUM(backlog_vacancies) * 100.0 / (SELECT SUM(backlog_vacancies) FROM d), 1)
FROM d
GROUP BY social_category
ORDER BY discipline, social_category;
