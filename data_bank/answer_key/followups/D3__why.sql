-- Answer Key Follow-up SQL: D3__why
-- Question: Why are DPC committee deliberations and promotion candidate lists classified as confidential?
-- Type: refusal
-- Semantic audit 2026-10-20: Old SQL cited Clause 3.0 (APAR benchmark) which does not address confidentiality.
-- Semantic audit 2026-10-20: Now cites R&P Clause 8.0 (Confidentiality of DPC Proceedings & Sealed Cover) and 7.0 (Vigilance clearance).

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(text, r'(?s)^.*?Glossary Terms:[^\n]*\n', ''), r'\s+', ' ')), 1, 400) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'R&P/Promotion' AND clause_ref IN ('Clause 8.0', 'Clause 7.0')
ORDER BY clause_ref DESC;
