-- Answer Key Follow-up SQL: D1__why
-- Question: Why is individual officer salary confidential under ONGC policy and CDA rules?
-- Type: refusal
-- Semantic audit 2026-10-20: Old SQL cited G-08 (Public Procurement / Make-in-India order) - irrelevant to salary confidentiality.
-- Semantic audit 2026-10-20: Now cites HR Manual Clause 5.0 (Confidentiality of Individual Compensation) and Clause 2.0 (published IDA scales = permitted alternative).

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(text, r'(?s)^.*?Glossary Terms:[^\n]*\n', ''), r'\s+', ' ')), 1, 400) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'HR Manual' AND clause_ref IN ('Clause 5.0', 'Clause 2.0')
ORDER BY clause_ref DESC;
