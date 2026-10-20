-- Answer Key Follow-up SQL: E4__why
-- Question: Why is promotion up to E4 time-bound subject to fitness, whereas E5 and above are merit-cum-seniority selections?
-- Type: policy
-- Semantic audit 2026-10-20: Old SQL cited Clause 4.0 and a non-existent Clause 9.0. Now Clause 2.0 (time-bound E1->E4, non-vacancy) and 4.0 (merit, vacancy-based E4->E5+).

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(text, r'(?s)^.*?Glossary Terms:[^\n]*\n', ''), r'\s+', ' ')), 1, 400) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'R&P/Promotion' AND clause_ref IN ('Clause 2.0', 'Clause 4.0')
ORDER BY doc_id, clause_ref;
