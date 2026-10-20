-- Answer Key SQL: X7
-- Question: Draft a reply to a Parliament question: "Vacancies in ONGC in the North-East region, category-wise."
-- Type: document
-- Semantic audit 2026-10-20: Category-wise as the Parliament question asks (old SQL was work-centre-wise with no category split).
-- All six NE work centres (Assam + Tripura), FY26 sanctioned-posts roster, by social category with state split.
SELECT
    sp.social_category AS category,
    SUM(sp.sanctioned_strength) AS sanctioned,
    SUM(sp.in_position_strength) AS in_position,
    SUM(sp.vacancy_count) AS vacancies,
    SUM(IF(wc.state = 'Assam', sp.vacancy_count, 0)) AS vacancies_assam,
    SUM(IF(wc.state = 'Tripura', sp.vacancy_count, 0)) AS vacancies_tripura,
    ROUND(SUM(sp.vacancy_count) * 100 / SUM(sp.sanctioned_strength), 1) AS vacancy_rate_pct,
    SUM(sp.backlog_vacancies) AS backlog_reserved_vacancies
FROM sanctioned_posts sp
JOIN dim_work_centre wc ON sp.wc_id = wc.wc_id
WHERE wc.sector = 'NE' AND sp.fiscal_year = 'FY26'
GROUP BY sp.social_category
ORDER BY CASE sp.social_category WHEN 'SC' THEN 1 WHEN 'ST' THEN 2 WHEN 'OBC' THEN 3 WHEN 'EWS' THEN 4 ELSE 5 END;
