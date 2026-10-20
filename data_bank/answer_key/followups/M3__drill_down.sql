-- Answer Key Follow-up SQL: M3__drill_down
-- Question: What is the authorized procedure for an executive to view their own APAR grading and salary slip on the ESS portal?
-- Type: refusal
-- Semantic audit 2026-10-20: Old SQL cited HR Manual Clause 1.0 (designation hierarchy), not the ESS self-service procedure, and quoted only header boilerplate.
-- Semantic audit 2026-10-20: Now: HR Manual Clause 4.0 (ESS portal - own payslip/APAR access), clause body quoted.

SELECT
    doc_id,
    clause_ref,
    heading,
    REGEXP_EXTRACT(text, r'\n\n([\s\S]*?) \(\d+\.1\)') AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'HR Manual' AND clause_ref = 'Clause 4.0'
ORDER BY clause_ref;
