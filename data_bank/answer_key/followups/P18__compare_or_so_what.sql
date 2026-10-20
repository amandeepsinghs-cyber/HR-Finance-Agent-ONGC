-- Answer Key Follow-up SQL: P18__compare_or_so_what
-- Question: Where can I view the published Job Rotation and Transfer Policy (JRTP) principles on the ONGC portal?
-- Type: refusal

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'JRTP' AND clause_ref = 'Clause 1.0')
ORDER BY doc_id, clause_ref
LIMIT 5;
