-- Answer Key SQL: H3
-- Question: What is the vacancy position (sanctioned vs. in-position) by asset and discipline?
-- Type: data
-- Semantic audit 2026-10-20: old SQL averaged row-level vacancy_rate_pct (unweighted mean of tiny category cells) and
-- truncated at LIMIT 100 ordered alphabetically (591 WC x discipline cells exist), and omitted sanctioned/in-position.
-- Now: FY26 sanctioned, in-position, vacancies and weighted vacancy rate per work centre x discipline, all cells, largest gaps first.
SELECT
    wc.short_name AS work_centre,
    d.name AS discipline,
    SUM(sp.sanctioned_strength) AS sanctioned,
    SUM(sp.in_position_strength) AS in_position,
    SUM(sp.vacancy_count) AS vacancies,
    ROUND(SUM(sp.vacancy_count) * 100.0 / NULLIF(SUM(sp.sanctioned_strength), 0), 1) AS vacancy_rate_pct,
    SUM(SUM(sp.sanctioned_strength)) OVER () AS company_sanctioned,
    SUM(SUM(sp.vacancy_count)) OVER () AS company_vacancies
FROM sanctioned_posts sp
JOIN dim_work_centre wc ON sp.wc_id = wc.wc_id
JOIN dim_discipline d ON sp.discipline_id = d.discipline_id
WHERE sp.fiscal_year = 'FY26'
GROUP BY wc.short_name, d.name
ORDER BY vacancies DESC, vacancy_rate_pct DESC, work_centre, discipline;
