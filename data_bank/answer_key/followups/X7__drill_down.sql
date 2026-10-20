-- Answer Key Follow-up SQL: X7__drill_down
-- Question: What are the exact sanctioned versus in-position numbers in Assam and Tripura broken down by SC, ST, OBC, EWS, and General?
-- Type: document
-- Semantic audit 2026-10-20: State-level (all NE work centres in Assam incl. Jorhat, A&AA Basin, Silchar, INBIGS - old SQL kept only
-- WC-ASM and WC-TRI) sanctioned vs in-position by category, FY26.
SELECT
    wc.state,
    sp.social_category AS category,
    SUM(sp.sanctioned_strength) AS sanctioned,
    SUM(sp.in_position_strength) AS in_position,
    SUM(sp.vacancy_count) AS vacancies,
    ROUND(SUM(sp.in_position_strength) * 100 / SUM(sp.sanctioned_strength), 1) AS fill_rate_pct
FROM sanctioned_posts sp
JOIN dim_work_centre wc ON sp.wc_id = wc.wc_id
WHERE wc.state IN ('Assam', 'Tripura') AND sp.fiscal_year = 'FY26'
GROUP BY wc.state, sp.social_category
ORDER BY wc.state, CASE sp.social_category WHEN 'SC' THEN 1 WHEN 'ST' THEN 2 WHEN 'OBC' THEN 3 WHEN 'EWS' THEN 4 ELSE 5 END;
