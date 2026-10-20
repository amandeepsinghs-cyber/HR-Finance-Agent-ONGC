-- Answer Key Follow-up SQL: H3__drill_down
-- Question: Which critical disciplines (Instrumentation, Petroleum, Chemical, Geophysics) have a vacancy deficit exceeding 15%?
-- Type: data
-- Semantic audit 2026-10-20: old SQL returned rates without applying the 15% threshold, omitted the petroleum disciplines
-- other than Production, and had no FY filter. Now: FY26 weighted vacancy rate for the named critical groups (Instrumentation;
-- Petroleum = Production, Drilling, Reservoir; Chemical = Chemistry; Geophysics), a >15% flag, and the number of work centres
-- (with >=10 sanctioned posts in the discipline) where the deficit exceeds 15%.
WITH cell AS (
    SELECT sp.discipline_id, sp.wc_id,
           SUM(sp.sanctioned_strength) AS sanctioned, SUM(sp.vacancy_count) AS vacancies
    FROM sanctioned_posts sp
    WHERE sp.fiscal_year = 'FY26'
    GROUP BY sp.discipline_id, sp.wc_id
)
SELECT
    d.name AS discipline,
    CASE WHEN d.name IN ('Production', 'Drilling', 'Reservoir') THEN 'Petroleum'
         WHEN d.name = 'Chemistry' THEN 'Chemical'
         WHEN STARTS_WITH(d.name, 'Geophysics') THEN 'Geophysics'
         ELSE d.name END AS critical_group,
    SUM(c.sanctioned) AS sanctioned,
    SUM(c.vacancies) AS vacancies,
    ROUND(SUM(c.vacancies) * 100.0 / NULLIF(SUM(c.sanctioned), 0), 1) AS vacancy_rate_pct,
    SUM(c.vacancies) * 100.0 / NULLIF(SUM(c.sanctioned), 0) > 15 AS exceeds_15pct,
    COUNTIF(c.sanctioned >= 10 AND c.vacancies * 100.0 / c.sanctioned > 15) AS work_centres_above_15pct,
    ROUND(MAX(IF(c.sanctioned >= 10, c.vacancies * 100.0 / c.sanctioned, NULL)), 1) AS worst_work_centre_rate_pct
FROM cell c
JOIN dim_discipline d ON d.discipline_id = c.discipline_id
WHERE d.name IN ('Instrumentation', 'Production', 'Drilling', 'Reservoir', 'Chemistry', 'Geophysics (Surface)', 'Geophysics (Wells)')
GROUP BY d.name
ORDER BY vacancy_rate_pct DESC;
