-- Answer Key Follow-up SQL: P10__drill_down
-- Question: What is the minimum qualifying residency period and aggregate APAR score threshold for E3 to E4 advancement?
-- Type: policy
-- Semantic audit 2026-10-20: old query returned only SUBSTR(text,1,300) = the chunk's metadata header
-- (title / glossary), never the clause body, so the answer key contained no actual rule. Now strips the
-- header and extracts the specific sub-clauses that answer the question (column `provision`).

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
)
SELECT doc_id, clause_ref, heading, provision, quote_snippet
FROM (
  SELECT 1 AS seq, doc_id, clause_ref, heading, 'R&P 2.1(c) (E3 residency)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(\(c\) Promotion from E3 to E4.*?) 2\.2 ')) AS quote_snippet
  FROM c WHERE doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 2.0'
  UNION ALL
  SELECT 2 AS seq, doc_id, clause_ref, heading, 'R&P 3.1(c) (E3 APAR benchmark)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(\(c\) For E3.E4.*?) 3\.2 ')) AS quote_snippet
  FROM c WHERE doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 3.0'
  UNION ALL
  SELECT 3 AS seq, doc_id, clause_ref, heading, 'R&P 3.2 (adverse remark deferral)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(3\.2 .*?) \(3\.1\)')) AS quote_snippet
  FROM c WHERE doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 3.0'
)
ORDER BY seq;
