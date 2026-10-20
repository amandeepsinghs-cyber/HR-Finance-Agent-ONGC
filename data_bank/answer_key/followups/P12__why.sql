-- Answer Key Follow-up SQL: P12__why
-- Question: Why is completion of a hard or North-East station tenure an essential policy prerequisite for managerial advancement to E5?
-- Type: policy_plus_data

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'JRTP' AND clause_ref = 'Clause 6.0')
ORDER BY doc_id, clause_ref
LIMIT 5;
