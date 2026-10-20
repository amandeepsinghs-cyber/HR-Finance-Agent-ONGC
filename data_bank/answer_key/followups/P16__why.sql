-- Answer Key Follow-up SQL: P16__why
-- Question: Why does the Book of Delegated Powers (BDP) require tender committee recommendations prior to Director sanction?
-- Type: policy_plus_data

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'BDP summary' AND clause_ref = 'Clause 7.0')
ORDER BY doc_id, clause_ref
LIMIT 5;
