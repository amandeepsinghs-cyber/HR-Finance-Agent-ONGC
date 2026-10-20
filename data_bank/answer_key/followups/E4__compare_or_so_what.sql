-- Answer Key Follow-up SQL: E4__compare_or_so_what
-- Question: How does the promotion timeline change if an executive completes an offshore or North-East hardship tenure?
-- Type: policy
-- Semantic audit 2026-10-20: Old SQL paired JRTP 6.0 with R&P 4.0. Now R&P Clause 5.0 (mandatory Cat-C / NE / 14x14 offshore tenure before E4->E5) with JRTP 6.0.

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(text, r'(?s)^.*?Glossary Terms:[^\n]*\n', ''), r'\s+', ' ')), 1, 400) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 5.0') OR (doc_id = 'JRTP' AND clause_ref = 'Clause 6.0')
ORDER BY doc_id, clause_ref;
