-- Answer Key Follow-up SQL: P5__drill_down
-- Question: What are the qualifying service criteria and approved postgraduate degree specializations for executive study leave?
-- Type: policy
-- Semantic audit 2026-10-20: old query returned only SUBSTR(text,1,300) = the chunk's metadata header
-- (title / glossary), never the clause body, so the answer key contained no actual rule. Now strips the
-- header and extracts the specific sub-clauses that answer the question (column `provision`).
-- Semantic audit 2026-10-20: GAP: no list of approved PG specialisations beyond the domain areas in 6.1.

WITH c AS (
  SELECT doc_id, clause_ref, heading,
         REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(text,
           r'(?s)^.*?Domain Vocabulary[^\n]*\n', ''),
           r'\\\\192\.168\.4\.1\\e\\Public Enterprises \(2018\)(\\4077PE)+\(Chapter 2\)', ' '),
           r'\d*\s*Chapter 2—Personnel Policies\s*\d*', ' '),
           r'Page \d+ of \d+', ' '),
           r'\s+', ' ') AS body
  FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
  WHERE (doc_id = 'Leave Rules' AND clause_ref = 'Clause 6.0')
)
SELECT doc_id, clause_ref, heading, provision, quote_snippet
FROM (
  SELECT 1 AS seq, doc_id, clause_ref, heading, 'Leave Rules 6.1-6.2' AS provision, TRIM(REGEXP_EXTRACT(body, r'(6\.1 .*?) 6\.3 ')) AS quote_snippet
  FROM c WHERE doc_id = 'Leave Rules' AND clause_ref = 'Clause 6.0'
)
ORDER BY seq;
