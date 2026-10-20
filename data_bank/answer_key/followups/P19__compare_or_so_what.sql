-- Answer Key Follow-up SQL: P19__compare_or_so_what
-- Question: How can an employee verify whether an expenditure approval has been sanctioned by a competent authority?
-- Type: refusal

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(text, 1, 300) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'BDP summary' AND clause_ref = 'Clause 7.0')
ORDER BY doc_id, clause_ref
LIMIT 5;
