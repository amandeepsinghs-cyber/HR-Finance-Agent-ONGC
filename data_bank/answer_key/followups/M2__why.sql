-- Answer Key Follow-up SQL: M2__why
-- Question: Why is financial capex utilisation accessible to Finance officers while restricted for junior HR officers?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL quoted only the chunk header boilerplate of BDP Clause 1.0.
-- Semantic audit 2026-10-20: Now: BDP Clause 1.0 (budget/BE-RE delegation to posts) and Clause 8.0 (controlled access to financial schedules), quoting the clause body. No explicit HR-vs-Finance functional RBAC clause exists (GAP).

SELECT
    doc_id,
    clause_ref,
    heading,
    REGEXP_EXTRACT(text, r'\n\n([\s\S]*?) \(\d+\.1\)') AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'BDP summary' AND clause_ref IN ('Clause 1.0', 'Clause 8.0')
ORDER BY clause_ref;
