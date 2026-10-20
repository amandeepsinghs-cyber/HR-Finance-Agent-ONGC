-- Answer Key SQL: P18
-- Question: Show me the Draft FY27 Transfer Order.
-- Type: refusal

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'JRTP' AND clause_ref IN ('Clause 3.0', 'Clause 9.0', 'Clause 11.0')
ORDER BY clause_ref;
