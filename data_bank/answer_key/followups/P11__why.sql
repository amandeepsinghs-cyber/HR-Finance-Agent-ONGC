-- Answer Key Follow-up SQL: P11__why
-- Question: Why have 31 senior executives been granted superannuation exemptions from the upcoming transfer order?
-- Type: policy_plus_data

SELECT doc_id, clause_ref, heading, SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'JRTP' AND clause_ref IN ('Clause 4.0', 'Clause 7.0')
ORDER BY clause_ref;
