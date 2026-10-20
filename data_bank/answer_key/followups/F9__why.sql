-- Answer Key Follow-up SQL: F9__why
-- Question: What treasury risk parameters and Board-approved hedging guidelines govern our forward derivative coverage?
-- Type: data
-- Semantic audit 2026-10-20: cited BDP Clause 5.0 (CMD delegated powers) which says nothing about hedging. The corpus has
-- Semantic audit 2026-10-20: no Board-approved hedging / treasury risk policy (GAP); the only governing provision found is
-- Semantic audit 2026-10-20: the DPE corporate-governance requirement to place quarterly foreign-exchange exposures and
-- Semantic audit 2026-10-20: risk-mitigation steps before the Board (G-04 2010 guidelines, repeated in G-06 compendium).

SELECT
    doc_id,
    clause_ref,
    SUBSTR(heading, 1, 120) AS heading,
    REGEXP_EXTRACT(REGEXP_REPLACE(SUBSTR(text, STRPOS(LOWER(text), 'quarterly details of foreign exchange'), 220), r'\s+', ' '), r'^(.*?if material\.)') AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE STRPOS(LOWER(text), 'quarterly details of foreign exchange') > 0
ORDER BY doc_id, clause_ref
LIMIT 5;
