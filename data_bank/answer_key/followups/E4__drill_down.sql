-- Answer Key Follow-up SQL: E4__drill_down
-- Question: What is the mandatory residency period (years of service) and minimum APAR benchmark score required for E2 to E3 promotion?
-- Type: policy
-- Semantic audit 2026-10-20: Old SQL cited Clause 4.0 (E4->E5 merit). Now Clause 2.0 (residency) and 3.0 (APAR benchmark) for E2->E3.

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(text, r'(?s)^.*?Glossary Terms:[^\n]*\n', ''), r'\s+', ' ')), 1, 400) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'R&P/Promotion' AND clause_ref IN ('Clause 2.0', 'Clause 3.0')
ORDER BY doc_id, clause_ref;
