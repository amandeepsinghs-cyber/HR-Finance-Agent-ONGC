-- Answer Key Follow-up SQL: E1__why
-- Question: Why is there a ceiling on maximum earned leave accumulation and encashment during active service versus retirement?
-- Type: data
-- Semantic audit 2026-10-20: Snippet hygiene only: quote now starts at the clause text instead of the document header/glossary (old SUBSTR(text,1,300) never reached the rule). Same clauses; dead LIMIT removed.

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(text, r'(?s)^.*?Glossary Terms:[^\n]*\n', ''), r'\s+', ' ')), 1, 400) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'Leave Rules' AND clause_ref IN ('Clause 3.0', 'Clause 4.0')
ORDER BY doc_id, clause_ref;
