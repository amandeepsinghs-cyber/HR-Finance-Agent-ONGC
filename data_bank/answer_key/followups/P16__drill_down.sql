-- Answer Key Follow-up SQL: P16__drill_down
-- Question: What are the specific approval limits for Director (T&FS), Director (Offshore), and the Executive Committee for drilling tenders?
-- Type: policy_plus_data

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'BDP summary' AND clause_ref = 'Clause 3.0') OR (doc_id = 'BDP summary' AND clause_ref = 'Clause 4.0')
ORDER BY doc_id, clause_ref
LIMIT 5;
