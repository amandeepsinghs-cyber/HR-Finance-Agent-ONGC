-- Answer Key Follow-up SQL: P1__drill_down
-- Question: What are the specific tenure limits for hard stations (Assam, Tripura, Silchar) versus normal stations?
-- Type: policy
-- Semantic audit 2026-10-20: old query returned only SUBSTR(text,1,300) = the chunk's metadata header
-- (title / glossary), never the clause body, so the answer key contained no actual rule. Now strips the
-- header and extracts the specific sub-clauses that answer the question (column `provision`).
-- Semantic audit 2026-10-20: Added JRTP 2.1(c) so the hard-station list (Assam, Tripura/Silchar, ...) is in the evidence.

WITH c AS (
  SELECT doc_id, clause_ref, heading,
         REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(text,
           r'(?s)^.*?Domain Vocabulary[^\n]*\n', ''),
           r'\\\\192\.168\.4\.1\\e\\Public Enterprises \(2018\)(\\4077PE)+\(Chapter 2\)', ' '),
           r'\d*\s*Chapter 2—Personnel Policies\s*\d*', ' '),
           r'Page \d+ of \d+', ' '),
           r'\s+', ' ') AS body
  FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
  WHERE (doc_id = 'JRTP' AND clause_ref = 'Clause 2.0')
     OR (doc_id = 'JRTP' AND clause_ref = 'Clause 3.0')
     OR (doc_id = 'JRTP' AND clause_ref = 'Clause 6.0')
)
SELECT doc_id, clause_ref, heading, provision, quote_snippet
FROM (
  SELECT 1 AS seq, doc_id, clause_ref, heading, 'JRTP 3.1-3.3 (normal stations)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(3\.1 .*?) 3\.4 ')) AS quote_snippet
  FROM c WHERE doc_id = 'JRTP' AND clause_ref = 'Clause 3.0'
  UNION ALL
  SELECT 2 AS seq, doc_id, clause_ref, heading, 'JRTP 2.1(c) (Category C hard stations)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(\(c\) Category .C. .*?) 2\.2 ')) AS quote_snippet
  FROM c WHERE doc_id = 'JRTP' AND clause_ref = 'Clause 2.0'
  UNION ALL
  SELECT 3 AS seq, doc_id, clause_ref, heading, 'JRTP 6.1-6.3 (hard-station tenure)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(6\.1 .*?) \(6\.1\)')) AS quote_snippet
  FROM c WHERE doc_id = 'JRTP' AND clause_ref = 'Clause 6.0'
)
ORDER BY seq;
