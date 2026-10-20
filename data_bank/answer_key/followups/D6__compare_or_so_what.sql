-- Answer Key Follow-up SQL: D6__compare_or_so_what
-- Question: What whistle-blower protection mechanisms exist under ONGC Vigilance guidelines?
-- Type: refusal
-- Semantic audit 2026-10-20: Old SQL returned arbitrary CDA-rule fragments identical to drill/why.
-- Semantic audit 2026-10-20: Now P2-01 Part 15 (no victimisation; complete protection) and Part 16 (disqualifications / malicious complaints).

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(text, r'(?s)^.*?Glossary Terms:[^\n]*\n', ''), r'\s+', ' ')), 1, 400) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'P2-01' AND clause_ref IN ('Part 15', 'Part 16') AND LOWER(confidentiality) = 'public'
ORDER BY doc_id, SAFE_CAST(REGEXP_EXTRACT(clause_ref, r'(\d+)') AS INT64);
