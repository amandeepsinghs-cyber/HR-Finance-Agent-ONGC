-- Answer Key Follow-up SQL: H7__why
-- Question: What logistical or facility barriers (accommodation, medical support) impact female officer deployment in offshore/remote fields?
-- Type: data
-- Semantic audit 2026-10-20: old SQL quoted the first 300 chars of the TA Regulations Part 1 header (document boilerplate,
-- irrelevant to women's offshore deployment). The corpus has no policy on offshore accommodation/facilities for women
-- (GAP); the only facility provision found is the female-medical-officer requirement in the Medical Examination Rules.
-- Now: the relevant passages (body text, not header) from P1-03 Parts 4 and 28.
SELECT doc_id, clause_ref, heading,
       TRIM(REGEXP_REPLACE(REGEXP_EXTRACT(text, r'(?is)([^.]{0,200}female medical officer[^.]*\.[^.]*\.?)'), r'\s+', ' ')) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'P1-03' AND clause_ref IN ('Part 4', 'Part 28')
ORDER BY clause_ref DESC;
