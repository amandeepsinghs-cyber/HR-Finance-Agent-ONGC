-- Answer Key Follow-up SQL: P15__why
-- Question: Why are statutory CSR funds prioritized in operational districts and national aspirational districts under Ministry guidelines?
-- Type: policy_plus_data

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'P2-10' OR doc_id LIKE 'P2-10%')
ORDER BY doc_id, clause_ref
LIMIT 5;
