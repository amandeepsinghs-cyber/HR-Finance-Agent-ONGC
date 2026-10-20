-- Answer Key Follow-up SQL: H10__why
-- Question: What replacement executives are proposed to ensure operational continuity in vacated corporate roles?
-- Type: document
-- Semantic audit 2026-10-20: old SQL quoted the first 300 chars of JRTP Clause 10.0 = header boilerplate only. Now: the clause
-- body (discipline-for-discipline replacement and asset-head certification) is quoted.
SELECT doc_id, clause_ref, heading,
       TRIM(SUBSTR(REGEXP_EXTRACT(text, r'(?s)\n\n(.*)'), 1, 700)) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'JRTP' AND clause_ref = 'Clause 10.0'
ORDER BY doc_id, clause_ref;
