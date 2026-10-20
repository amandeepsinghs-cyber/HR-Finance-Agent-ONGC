-- Answer Key Follow-up SQL: P9__drill_down
-- Question: Who are the external members and Presiding Officers of the Internal Complaints Committee (ICC) at my work centre?
-- Type: policy
-- Semantic audit 2026-10-20: old output was the parent's committee list with NGO swapped in (near-duplicate).
-- Now profiles the external members (how many ICCs each sits on) and presiding-officer composition.

SELECT
    external_member_name,
    external_member_ngo,
    COUNT(*) AS committees,
    STRING_AGG(wc_id, ', ' ORDER BY wc_id) AS work_centres,
    COUNTIF(LOWER(presiding_officer_gender) = 'female') AS female_presiding_officers,
    COUNT(DISTINCT presiding_officer_name) AS distinct_presiding_officer_names,
    MIN(women_members_pct) AS min_women_members_pct
FROM icc_committees
WHERE LOWER(status) = 'active'
GROUP BY external_member_name, external_member_ngo
ORDER BY committees DESC, external_member_name;
