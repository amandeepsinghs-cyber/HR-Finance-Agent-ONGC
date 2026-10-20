-- Answer Key Follow-up SQL: H6__compare_or_so_what
-- Question: How do our current roster representation percentages compare against statutory presidential directives and DoPT guidelines?
-- Type: data
-- Semantic audit 2026-10-20: old SQL reported in-position/sanctioned fill rate per category (not representation) with no norm
-- and no FY filter. Now: company FY26 representation of each reserved category vs statutory norm, gap and backlog.
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
    c.category,
    SUM(c.in_position) AS in_position,
    (SELECT SUM(in_position_strength) FROM posts) AS company_in_position,
    ROUND(SUM(c.in_position) * 100.0 / (SELECT SUM(in_position_strength) FROM posts), 2) AS representation_pct,
    n.norm_pct,
    ROUND(SUM(c.in_position) * 100.0 / (SELECT SUM(in_position_strength) FROM posts) - n.norm_pct, 2) AS gap_vs_norm_pp,
    SUM(c.backlog_vacancies) AS backlog_vacancies
FROM by_cat c
JOIN norms n ON n.category = c.category
GROUP BY c.category, n.norm_pct
ORDER BY gap_vs_norm_pp;
