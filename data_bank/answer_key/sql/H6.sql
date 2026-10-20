-- Answer Key SQL: H6
-- Question: Are we compliant with reservation norms (SC/ST/OBC/EWS/PwD) by grade?
-- Type: data
-- Semantic audit 2026-10-20: old SQL LEFT JOINed employee_master on discipline_id (fan-out weighting every cell by the
-- discipline's headcount) and reported fill rate (in-position/sanctioned) instead of representation vs norm; PwD absent.
-- Now: FY26 in-position representation of SC/ST/OBC/EWS/PwD as % of the grade's in-position strength vs statutory norm,
-- with backlog reserved vacancies, by grade (board posts excluded).
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
    c.in_position,
    t.grade_in_position,
    ROUND(c.in_position * 100.0 / t.grade_in_position, 1) AS representation_pct,
    n.norm_pct,
    ROUND(c.in_position * 100.0 / t.grade_in_position - n.norm_pct, 1) AS gap_vs_norm_pp,
    c.backlog_vacancies,
    c.in_position * 100.0 / t.grade_in_position >= n.norm_pct AS meets_norm
FROM by_cat c
JOIN grade_tot t ON t.grade_id = c.grade_id
JOIN norms n ON n.category = c.category
JOIN dim_grade g ON g.grade_id = c.grade_id
WHERE LOWER(g.cadre) <> 'board'
ORDER BY g.level_order, n.norm_pct DESC, c.category;
