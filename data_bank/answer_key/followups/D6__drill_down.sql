-- Answer Key Follow-up SQL: D6__drill_down
-- Question: What is the standard procedure for reporting a vigilance concern or submitting a complaint in ONGC?
-- Type: refusal
-- Semantic audit 2026-10-20: Old SQL returned arbitrary CDA-rule fragments (P1-01, LIMIT 5) - not the reporting procedure.
-- Semantic audit 2026-10-20: Now P2-01 Part 7 (whom/how to report, 30-day window), Part 8 (sealed envelope / vigil@ongc.co.in) and Part 10 (screening committee).

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(text, r'(?s)^.*?Glossary Terms:[^\n]*\n', ''), r'\s+', ' ')), 1, 400) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'P2-01' AND clause_ref IN ('Part 7', 'Part 8', 'Part 10') AND LOWER(confidentiality) = 'public'
ORDER BY doc_id, SAFE_CAST(REGEXP_EXTRACT(clause_ref, r'(\d+)') AS INT64);
