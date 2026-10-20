-- Answer Key SQL: P10
-- Question: What are the criteria for promotion from E3 to E4?
-- Type: policy
-- Semantic audit 2026-10-20: old query returned only SUBSTR(text,1,300) = the chunk's metadata header
-- (title / glossary), never the clause body, so the answer key contained no actual rule. Now strips the
-- header and extracts the specific sub-clauses that answer the question (column `provision`).
-- Semantic audit 2026-10-20: Old query returned only the Clause 2.0 header; APAR benchmark and vigilance clearance were missing.

WITH c AS (
  SELECT doc_id, clause_ref, heading,
         REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(text,
           r'(?s)^.*?Domain Vocabulary[^\n]*\n', ''),
           r'\\\\192\.168\.4\.1\\e\\Public Enterprises \(2018\)(\\4077PE)+\(Chapter 2\)', ' '),
           r'\d*\s*Chapter 2—Personnel Policies\s*\d*', ' '),
           r'Page \d+ of \d+', ' '),
           r'\s+', ' ') AS body
  FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
  WHERE (doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 2.0')
     OR (doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 3.0')
     OR (doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 7.0')
)
SELECT doc_id, clause_ref, heading, provision, quote_snippet
FROM (
  SELECT 1 AS seq, doc_id, clause_ref, heading, 'R&P 2.1-2.3 (time-bound channel)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(2\.1 .*?) \(2\.1\)')) AS quote_snippet
  FROM c WHERE doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 2.0'
  UNION ALL
  SELECT 2 AS seq, doc_id, clause_ref, heading, 'R&P 3.1-3.2 (APAR benchmark)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(3\.1 .*?) \(3\.1\)')) AS quote_snippet
  FROM c WHERE doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 3.0'
  UNION ALL
  SELECT 3 AS seq, doc_id, clause_ref, heading, 'R&P 7.1-7.2 (vigilance clearance)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(7\.1 .*?) \(7\.1\)')) AS quote_snippet
  FROM c WHERE doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 7.0'
)
ORDER BY seq;
