-- Answer Key Follow-up SQL: D3__compare_or_so_what
-- Question: When is the final DPC promotion result scheduled to be formally published on the ONGC intranet?
-- Type: refusal
-- Semantic audit 2026-10-20: Old SQL cited Clause 3.0 (APAR benchmark) - irrelevant to when results are published.
-- Semantic audit 2026-10-20: Now cites R&P Clause 2.0 (2.3: promotions effective 1 Jan / 1 Jul) and 8.0 (panel released officially; sealed cover). No fixed intranet date exists in the corpus (GAP).

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(text, r'(?s)^.*?Glossary Terms:[^\n]*\n', ''), r'\s+', ' ')), 1, 400) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'R&P/Promotion' AND clause_ref IN ('Clause 2.0', 'Clause 8.0')
ORDER BY doc_id, clause_ref;
