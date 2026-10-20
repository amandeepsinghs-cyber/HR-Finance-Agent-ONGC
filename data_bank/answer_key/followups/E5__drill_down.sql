-- Answer Key Follow-up SQL: E5__drill_down
-- Question: What is the daily offshore hardship allowance rate and special conveyance entitlement for an E2 engineer?
-- Type: policy
-- Semantic audit 2026-10-20: Old SQL cited P1-16 Part 2 (definitions). Now JRTP 6.0 with the 6.3 allowance text as the quote; no per-day offshore rate or conveyance amount exists in the corpus (GAP).

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(REGEXP_REPLACE(REGEXP_EXTRACT(text, r'(?s)(6\.3 .*)'), r'\s+', ' '), 1, 400) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'JRTP' AND clause_ref = 'Clause 6.0';
