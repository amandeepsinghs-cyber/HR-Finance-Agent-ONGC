-- Answer Key Follow-up SQL: M4__why
-- Question: Why is field-level profitability confidential and restricted from junior functional officers?
-- Type: refusal
-- Semantic audit 2026-10-20: Old SQL quoted only the chunk header boilerplate.
-- Semantic audit 2026-10-20: Now: BDP Clause 8.0 body (commercially sensitive, internal controlled classification).

SELECT
    doc_id,
    clause_ref,
    heading,
    REGEXP_EXTRACT(text, r'\n\n([\s\S]*?) \(\d+\.1\)') AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'BDP summary' AND clause_ref = 'Clause 8.0'
ORDER BY clause_ref;
