-- Answer Key Follow-up SQL: M3__why
-- Question: Why are individual salary and APAR appraisals classified as strictly confidential personal data?
-- Type: refusal
-- Semantic audit 2026-10-20: Old SQL cited G-08 (Make-in-India public procurement order) - irrelevant to salary/APAR confidentiality.
-- Semantic audit 2026-10-20: Now: HR Manual Clause 5.0 (colleague salary/APAR = protected personal data, RTI 8(1)(j), CDA Rules 4/11) and R&P Promotion Clause 8.0 (DPC/appraisal secrecy).

SELECT
    doc_id,
    clause_ref,
    heading,
    REGEXP_EXTRACT(text, r'\n\n([\s\S]*?) \(\d+\.1\)') AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'HR Manual' AND clause_ref = 'Clause 5.0') OR (doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 8.0')
ORDER BY doc_id, clause_ref;
