-- Answer Key SQL: E5
-- Question: What is the TA/DA entitlement for an offshore posting?
-- Type: policy
-- Semantic audit 2026-10-20: Old SQL cited P1-16 Part 1 (title/applicability text) - no offshore entitlement.
-- Semantic audit 2026-10-20: Now JRTP 6.0 (6.3: hard-station allowance 10% BP; 14x14 offshore is Cat-C), P1-16 Part 10 (14-day on/off staff fly economy/Y class) and Part 38 (DA cut to 1/4 when free board & lodging provided).

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(text, r'(?s)^.*?Glossary Terms:[^\n]*\n', ''), r'\s+', ' ')), 1, 400) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'JRTP' AND clause_ref = 'Clause 6.0') OR (doc_id = 'P1-16' AND clause_ref IN ('Part 10', 'Part 38'))
ORDER BY doc_id, clause_ref;
