-- Answer Key Follow-up SQL: H3__compare_or_so_what
-- Question: How does the executive vacancy rate in Assam Asset compare with Western Onshore assets (Mehsana, Ahmedabad)?
-- Type: data
-- Semantic audit 2026-10-20: old SQL computed the rate over ALL grades although the question asks for EXECUTIVE vacancy rate.
-- Now: FY26 executive (cadre='executive') sanctioned/vacancy rate for Assam, Mehsana, Ahmedabad plus the company executive rate.
SELECT
    wc.short_name AS work_centre,
    SUM(sp.sanctioned_strength) AS exec_sanctioned,
    SUM(sp.in_position_strength) AS exec_in_position,
    SUM(sp.vacancy_count) AS exec_vacancies,
    ROUND(SUM(sp.vacancy_count) * 100.0 / NULLIF(SUM(sp.sanctioned_strength), 0), 1) AS exec_vacancy_rate_pct
FROM sanctioned_posts sp
JOIN dim_work_centre wc ON sp.wc_id = wc.wc_id
JOIN dim_grade g ON g.grade_id = sp.grade_id
WHERE sp.fiscal_year = 'FY26' AND LOWER(g.cadre) = 'executive'
  AND wc.short_name IN ('Assam Asset', 'Mehsana Asset', 'Ahmedabad Asset')
GROUP BY wc.short_name
UNION ALL
SELECT 'All work centres', SUM(sp.sanctioned_strength), SUM(sp.in_position_strength), SUM(sp.vacancy_count),
       ROUND(SUM(sp.vacancy_count) * 100.0 / NULLIF(SUM(sp.sanctioned_strength), 0), 1)
FROM sanctioned_posts sp
JOIN dim_grade g ON g.grade_id = sp.grade_id
WHERE sp.fiscal_year = 'FY26' AND LOWER(g.cadre) = 'executive'
ORDER BY exec_vacancy_rate_pct DESC;
