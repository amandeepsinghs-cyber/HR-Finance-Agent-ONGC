-- Answer Key Follow-up SQL: P18__drill_down
-- Question: What are the general guidelines, cut-off dates, and timeline for publishing the final FY27 transfer order?
-- Type: refusal

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'JRTP' AND clause_ref = 'Clause 9.0')
ORDER BY doc_id, clause_ref
LIMIT 5;
