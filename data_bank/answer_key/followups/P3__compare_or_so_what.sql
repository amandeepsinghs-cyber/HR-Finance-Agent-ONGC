-- Answer Key Follow-up SQL: P3__compare_or_so_what
-- Question: How does the transfer exemption policy apply to medical hardship or spouse-ground cases compared to retirement?
-- Type: policy
-- Semantic audit 2026-10-20: old query returned only SUBSTR(text,1,300) = the chunk's metadata header
-- (title / glossary), never the clause body, so the answer key contained no actual rule. Now strips the
-- header and extracts the specific sub-clauses that answer the question (column `provision`).
-- Semantic audit 2026-10-20: Added Clause 13 (spouse ground lives there, not in Clause 8).

WITH c AS (
  SELECT doc_id, clause_ref, heading,
         REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(text,
           r'(?s)^.*?Domain Vocabulary[^\n]*\n', ''),
           r'\\\\192\.168\.4\.1\\e\\Public Enterprises \(2018\)(\\4077PE)+\(Chapter 2\)', ' '),
           r'\d*\s*Chapter 2—Personnel Policies\s*\d*', ' '),
           r'Page \d+ of \d+', ' '),
           r'\s+', ' ') AS body
  FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
  WHERE (doc_id = 'JRTP' AND clause_ref = 'Clause 13.0')
     OR (doc_id = 'JRTP' AND clause_ref = 'Clause 7.0')
     OR (doc_id = 'JRTP' AND clause_ref = 'Clause 8.0')
)
SELECT doc_id, clause_ref, heading, provision, quote_snippet
FROM (
  SELECT 1 AS seq, doc_id, clause_ref, heading, 'JRTP 8.1-8.3 (medical)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(8\.1 .*?) \(8\.1\)')) AS quote_snippet
  FROM c WHERE doc_id = 'JRTP' AND clause_ref = 'Clause 8.0'
  UNION ALL
  SELECT 2 AS seq, doc_id, clause_ref, heading, 'JRTP 13.1-13.3 (spouse / representation)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(13\.1 .*?) \(13\.1\)')) AS quote_snippet
  FROM c WHERE doc_id = 'JRTP' AND clause_ref = 'Clause 13.0'
  UNION ALL
  SELECT 3 AS seq, doc_id, clause_ref, heading, 'JRTP 7.1 (retirement)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(7\.1 .*?) 7\.2 ')) AS quote_snippet
  FROM c WHERE doc_id = 'JRTP' AND clause_ref = 'Clause 7.0'
)
ORDER BY seq;
