-- Answer Key Follow-up SQL: P19__drill_down
-- Question: What are the general financial authorities delegated to Key Executives / Level-1 managers for day-to-day operations?
-- Type: refusal

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'BDP summary' AND clause_ref = 'Clause 2.0')
ORDER BY doc_id, clause_ref
LIMIT 5;
