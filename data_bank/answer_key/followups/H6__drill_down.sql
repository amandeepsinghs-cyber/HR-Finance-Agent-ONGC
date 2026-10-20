-- Answer Key Follow-up SQL: H6__drill_down
-- Question: What is the exact representation percentage and backlog vacancy count for SC, ST, OBC, EWS, and PwD in E1 to E7?
-- Type: data
-- Semantic audit 2026-10-20: old SQL returned only backlog counts (no representation %) and no FY filter. Now: FY26 E1-E7,
-- per category: reserved sanctioned posts, in-position, representation % of the grade, category vacancies and backlog.
WITH posts AS (
    SELECT sp.*,
           IF(LOWER(IFNULL(sp.pwd_category, 'none')) IN ('none', ''), FALSE, TRUE) AS is_pwd
    FROM sanctioned_posts sp
    WHERE sp.fiscal_year = 'FY26'
),
by_cat AS (
    SELECT grade_id, social_category AS category, SUM(sanctioned_strength) AS sanctioned, SUM(in_position_strength) AS in_position,
           SUM(vacancy_count) AS vacancies, SUM(backlog_vacancies) AS backlog_vacancies
    FROM posts WHERE LOWER(social_category) IN ('sc', 'st', 'obc', 'ews')
    GROUP BY 1, 2
    UNION ALL
    SELECT grade_id, 'PwD', SUM(sanctioned_strength), SUM(in_position_strength), SUM(vacancy_count), SUM(backlog_vacancies)
    FROM posts WHERE is_pwd
    GROUP BY 1
),
grade_tot AS (
    SELECT grade_id, SUM(in_position_strength) AS grade_in_position, SUM(sanctioned_strength) AS grade_sanctioned
    FROM posts GROUP BY 1
),
norms AS (
    -- statutory reservation norms (DoPT / Presidential directives): SC 15%, ST 7.5%, OBC 27%, EWS 10%, PwD 4%
    SELECT 'SC' AS category, 15.0 AS norm_pct UNION ALL SELECT 'ST', 7.5 UNION ALL SELECT 'OBC', 27.0
    UNION ALL SELECT 'EWS', 10.0 UNION ALL SELECT 'PwD', 4.0
)
SELECT
    c.grade_id,
    c.category,
    c.sanctioned AS reserved_sanctioned,
    c.in_position,
    ROUND(c.in_position * 100.0 / t.grade_in_position, 1) AS representation_pct,
    n.norm_pct,
    c.vacancies AS category_vacancies,
    c.backlog_vacancies
FROM by_cat c
JOIN grade_tot t ON t.grade_id = c.grade_id
JOIN norms n ON n.category = c.category
WHERE c.grade_id IN ('E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7')
ORDER BY c.grade_id, n.norm_pct DESC, c.category;
