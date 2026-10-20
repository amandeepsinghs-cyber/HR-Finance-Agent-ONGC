-- Answer Key SQL: P5
-- Question: Am I eligible for study leave, and what bond applies?
-- Type: policy
-- Semantic audit 2026-10-20: old query returned only SUBSTR(text,1,300) = the chunk's metadata header
-- (title / glossary), never the clause body, so the answer key contained no actual rule. Now strips the
-- header and extracts the specific sub-clauses that answer the question (column `provision`).
-- Semantic audit 2026-10-20: Dropped the OR'd J-08 judgment (Mahalkar, EOL) that filled LIMIT 5 and pushed both Leave Rules clauses out.

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
     OR (doc_id = 'Leave Rules' AND clause_ref = 'Clause 7.0')
)
SELECT doc_id, clause_ref, heading, provision, quote_snippet
FROM (
  SELECT 1 AS seq, doc_id, clause_ref, heading, 'Leave Rules 6.1-6.4' AS provision, TRIM(REGEXP_EXTRACT(body, r'(6\.1 .*?) \(6\.1\)')) AS quote_snippet
  FROM c WHERE doc_id = 'Leave Rules' AND clause_ref = 'Clause 6.0'
  UNION ALL
  SELECT 2 AS seq, doc_id, clause_ref, heading, 'Leave Rules 7.1-7.2' AS provision, TRIM(REGEXP_EXTRACT(body, r'(7\.1 .*?) \(7\.1\)')) AS quote_snippet
  FROM c WHERE doc_id = 'Leave Rules' AND clause_ref = 'Clause 7.0'
)
ORDER BY seq;
