-- Answer Key Follow-up SQL: P8__compare_or_so_what
-- Question: How does a formal Whistle Blower disclosure differ procedurally from an ordinary employee grievance petition?
-- Type: policy
-- Semantic audit 2026-10-20: old query returned only SUBSTR(text,1,300) = the chunk's metadata header
-- (title / glossary), never the clause body, so the answer key contained no actual rule. Now strips the
-- header and extracts the specific sub-clauses that answer the question (column `provision`).
-- Semantic audit 2026-10-20: Old query returned Part 4 (definitions) only.

WITH c AS (
  SELECT doc_id, clause_ref, heading,
         REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(text,
           r'(?s)^.*?Domain Vocabulary[^\n]*\n', ''),
           r'\\\\192\.168\.4\.1\\e\\Public Enterprises \(2018\)(\\4077PE)+\(Chapter 2\)', ' '),
           r'\d*\s*Chapter 2—Personnel Policies\s*\d*', ' '),
           r'Page \d+ of \d+', ' '),
           r'\s+', ' ') AS body
  FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
  WHERE (doc_id = 'P2-01' AND clause_ref = 'Part 11')
     OR (doc_id = 'P2-01' AND clause_ref = 'Part 13')
     OR (doc_id = 'P2-01' AND clause_ref = 'Part 5')
     OR (doc_id = 'P2-16' AND clause_ref = 'Part 8')
)
SELECT doc_id, clause_ref, heading, provision, quote_snippet
FROM (
  SELECT 1 AS seq, doc_id, clause_ref, heading, 'WBP 4.9 (personal grievance excluded)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(4\.9 .*)$')) AS quote_snippet
  FROM c WHERE doc_id = 'P2-01' AND clause_ref = 'Part 5'
  UNION ALL
  SELECT 2 AS seq, doc_id, clause_ref, heading, 'WBP 9.3 (screening in 10 working days)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(9\.3 .*?) 9\.4 ')) AS quote_snippet
  FROM c WHERE doc_id = 'P2-01' AND clause_ref = 'Part 11'
  UNION ALL
  SELECT 3 AS seq, doc_id, clause_ref, heading, 'WBP 9.15 (investigation in 120 days)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(9\.15 .*?) 9\.16 ')) AS quote_snippet
  FROM c WHERE doc_id = 'P2-01' AND clause_ref = 'Part 13'
  UNION ALL
  SELECT 4 AS seq, doc_id, clause_ref, heading, 'Human Rights Policy 4 (grievance systems)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(4\. Grievance Redressal.*)$')) AS quote_snippet
  FROM c WHERE doc_id = 'P2-16' AND clause_ref = 'Part 8'
)
ORDER BY seq;
