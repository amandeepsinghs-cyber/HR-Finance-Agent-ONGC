-- Answer Key Follow-up SQL: H9__why
-- Question: What institutional delays in the internal grievance redressal mechanism contributed to cases escalating to litigation?
-- Type: data
-- Semantic audit 2026-10-20: old SQL quoted the first 300 chars of JRTP Clause 13.0 = document header boilerplate with no
-- substantive text. Now: the clause body (time-bound TGRC disposal rules) is quoted. The corpus holds no general employee
-- grievance-redressal policy, so JRTP 13.0 (transfer grievances) is the closest provision (partial GAP).
SELECT doc_id, clause_ref, heading,
       TRIM(SUBSTR(REGEXP_EXTRACT(text, r'(?s)\n\n(.*)'), 1, 700)) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'JRTP' AND clause_ref = 'Clause 13.0'
ORDER BY doc_id, clause_ref;
