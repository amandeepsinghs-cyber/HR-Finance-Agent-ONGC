-- Answer Key Follow-up SQL: D6__why
-- Question: Why is vigilance inquiry status confidential and exempt from disclosure?
-- Type: refusal
-- Semantic audit 2026-10-20: Old SQL returned arbitrary CDA-rule fragments identical to drill/compare.
-- Semantic audit 2026-10-20: Now P2-01 Part 9 (identities kept confidential), Part 12 (subject's rights during investigation) and R&P Clause 8.0 (sealed cover).

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(text, r'(?s)^.*?Glossary Terms:[^\n]*\n', ''), r'\s+', ' ')), 1, 400) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE ((doc_id = 'P2-01' AND clause_ref IN ('Part 9', 'Part 12')) OR (doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 8.0'))
ORDER BY doc_id, SAFE_CAST(REGEXP_EXTRACT(clause_ref, r'(\d+)') AS INT64);
