-- Answer Key Follow-up SQL: P16__compare_or_so_what
-- Question: How do financial approval thresholds differ between single-source / nomination procurement and open competitive bidding?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Cited Clause 1.0 (general principles); open vs limited vs single/proprietary tender limits are in Clause 2.0 (2.1/2.2).

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'BDP summary' AND clause_ref = 'Clause 2.0')
ORDER BY doc_id, clause_ref
LIMIT 5;
