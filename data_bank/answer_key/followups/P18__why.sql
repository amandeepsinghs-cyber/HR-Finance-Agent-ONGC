-- Answer Key Follow-up SQL: P18__why
-- Question: Why is the draft transfer proposal strictly confidential prior to official approval by Director (HR) and CMD?
-- Type: refusal

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'JRTP' AND clause_ref = 'Clause 11.0')
ORDER BY doc_id, clause_ref
LIMIT 5;
