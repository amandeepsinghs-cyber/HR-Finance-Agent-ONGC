-- Answer Key Follow-up SQL: P20__drill_down
-- Question: What is the general Board-approved framework for offering mature fields under Production Enhancement Contracts (PEC)?
-- Type: refusal

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'BDP summary' AND clause_ref = 'Clause 6.0')
ORDER BY doc_id, clause_ref
LIMIT 5;
