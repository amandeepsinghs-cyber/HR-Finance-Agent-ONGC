-- Answer Key Follow-up SQL: M1__why
-- Question: Why is aggregate asset-level headcount accessible to HR officers but restricted from general Finance officers?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL cited G-08 (Make-in-India procurement order) and a non-existent P1-01 Clause 5.0, and quoted only the chunk header boilerplate.
-- Semantic audit 2026-10-20: Now: the closest access-control clauses (JRTP 11.0 role-based access to HR records; HR Manual 5.0 personal-data confidentiality), quoting the clause body. No explicit HR-vs-Finance functional RBAC clause exists in the corpus (GAP).

SELECT
    doc_id,
    clause_ref,
    heading,
    REGEXP_EXTRACT(text, r'\n\n([\s\S]*?) \(\d+\.1\)') AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'JRTP' AND clause_ref = 'Clause 11.0') OR (doc_id = 'HR Manual' AND clause_ref = 'Clause 5.0')
ORDER BY doc_id DESC, clause_ref;
