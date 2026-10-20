-- Answer Key Follow-up SQL: P13__why
-- Question: Why does the DPE guidelines prohibit employer contribution towards superannuation benefits exceeding 30%?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Cited PRBS Clause 1.0 (Trust constitution); the 30% ceiling and its components are in PRBS Clause 3.0.

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'PRBS' AND clause_ref = 'Clause 3.0')
ORDER BY doc_id, clause_ref
LIMIT 5;
