-- Answer Key Follow-up SQL: P19__why
-- Question: Why are detailed Director and Board financial authorities restricted from full disclosure to general staff?
-- Type: refusal

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'BDP summary' AND clause_ref = 'Clause 8.0')
ORDER BY doc_id, clause_ref
LIMIT 5;
