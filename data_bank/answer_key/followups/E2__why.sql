-- Answer Key Follow-up SQL: E2__why
-- Question: What specific criteria under the Job Rotation and Transfer Policy (JRTP) determine my priority for transfer in the upcoming cycle?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Snippet hygiene only: quote now starts at the clause text instead of the document header/glossary (old SUBSTR(text,1,300) never reached the rule). Same clauses; dead LIMIT removed.

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(text, r'(?s)^.*?Glossary Terms:[^\n]*\n', ''), r'\s+', ' ')), 1, 400) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'JRTP' AND clause_ref IN ('Clause 3.0', 'Clause 9.0')
ORDER BY doc_id, clause_ref;
