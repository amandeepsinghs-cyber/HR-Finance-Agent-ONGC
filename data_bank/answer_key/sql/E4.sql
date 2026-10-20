-- Answer Key SQL: E4
-- Question: What are the eligibility criteria for promotion from E2 to E3?
-- Type: policy
-- Semantic audit 2026-10-20: Old SQL: J-15 court-judgment fragments filled LIMIT 5 (sort before 'R&P'), and the R&P clause targeted was 4.0 (E4->E5 merit channel) - wrong grade.
-- Semantic audit 2026-10-20: Now R&P Clause 2.0 (E2->E3: 3 yrs residency, time-bound), 3.0 (APAR >= 3.5 / 70%) and 7.0 (vigilance clearance).

SELECT
    doc_id,
    clause_ref,
    heading,
    SUBSTR(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(text, r'(?s)^.*?Glossary Terms:[^\n]*\n', ''), r'\s+', ' ')), 1, 400) AS quote_snippet
FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
WHERE doc_id = 'R&P/Promotion' AND clause_ref IN ('Clause 2.0', 'Clause 3.0', 'Clause 7.0')
ORDER BY doc_id, clause_ref;
