-- Answer Key Follow-up SQL: X2__why
-- Question: What statutory compliance guidelines (Contract Labour Regulation & Abolition Act) govern deployment in core operational activities?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL cited HR Manual Clause 1.0 (executive designations) - unrelated to contract labour.
-- GAP: the Contract Labour (Regulation & Abolition) Act text is not in hrfin_docs; the closest corpus authorities on
-- deploying contract labour in ONGC are the Gujarat HC judgment J-14, the Industrial Tribunal/SC matter J-17 and the
-- Supplier Code of Conduct P2-17. Snippets are centred on the contract-labour passage.
SELECT
    doc_id,
    clause_ref,
    heading,
    TRIM(REGEXP_EXTRACT(text, r'(?is)(.{0,200}contract.{0,400})')) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE (doc_id = 'J-14' AND STARTS_WITH(clause_ref, '4 of that Act'))
   OR (doc_id = 'J-17' AND clause_ref = 'Part 5')
   OR (doc_id = 'P2-17' AND clause_ref = 'Part 2')
ORDER BY CASE doc_id WHEN 'J-14' THEN 1 WHEN 'J-17' THEN 2 ELSE 3 END;
