-- Answer Key Follow-up SQL: P14__why
-- Question: Why does the DPE PRP computation formula scale bonus multipliers steeply based on company MoU performance grades?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Cited PRBS Clause 1.0 (pension trust, unrelated). PRP rating multipliers are in DPE OM 2017 (G-01) Parts 13-15.

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'G-01' AND clause_ref IN ('Part 13', 'Part 14', 'Part 15')
ORDER BY doc_id, clause_ref
LIMIT 5;
