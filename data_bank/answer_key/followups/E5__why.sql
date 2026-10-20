-- Answer Key Follow-up SQL: E5__why
-- Question: What safety, travel time, and operational guidelines govern the 14-day on / 14-day off rotational shift allowance?
-- Type: policy
-- Semantic audit 2026-10-20: Old SQL cited P1-16 Part 3 (family definition). Now P1-16 Part 10 (14-day on/off travel provision) and R&P 5.0 (14x14 offshore duty counts as hard-station tenure). No safety/travel-time guideline exists in the corpus (GAP).

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(text, r'(?s)^.*?Glossary Terms:[^\n]*\n', ''), r'\s+', ' ')), 1, 400) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'P1-16' AND clause_ref = 'Part 10') OR (doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 5.0')
ORDER BY doc_id, clause_ref;
