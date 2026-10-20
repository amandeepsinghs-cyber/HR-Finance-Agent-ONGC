-- Answer Key SQL: P8
-- Question: How do I raise a concern confidentially without being victimised?
-- Type: policy
-- Semantic audit 2026-10-20: old query returned only SUBSTR(text,1,300) = the chunk's metadata header
-- (title / glossary), never the clause body, so the answer key contained no actual rule. Now strips the
-- header and extracts the specific sub-clauses that answer the question (column `provision`).
-- Semantic audit 2026-10-20: Old query returned Part 1 (preface) only.

WITH c AS (
  SELECT doc_id, clause_ref, heading,
         REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(text,
           r'(?s)^.*?Domain Vocabulary[^\n]*\n', ''),
           r'\\\\192\.168\.4\.1\\e\\Public Enterprises \(2018\)(\\4077PE)+\(Chapter 2\)', ' '),
           r'\d*\s*Chapter 2—Personnel Policies\s*\d*', ' '),
           r'Page \d+ of \d+', ' '),
           r'\s+', ' ') AS body
  FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
  WHERE (doc_id = 'P2-01' AND clause_ref = 'Part 15')
     OR (doc_id = 'P2-01' AND clause_ref = 'Part 7')
     OR (doc_id = 'P2-01' AND clause_ref = 'Part 8')
)
SELECT doc_id, clause_ref, heading, provision, quote_snippet
FROM (
  SELECT 1 AS seq, doc_id, clause_ref, heading, 'WBP 7.1-7.2 (where/when to file)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(7\.1 .*)$')) AS quote_snippet
  FROM c WHERE doc_id = 'P2-01' AND clause_ref = 'Part 7'
  UNION ALL
  SELECT 2 AS seq, doc_id, clause_ref, heading, 'WBP 7.3-7.5 (sealed envelope, identity concealed)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(7\.3 .*)$')) AS quote_snippet
  FROM c WHERE doc_id = 'P2-01' AND clause_ref = 'Part 8'
  UNION ALL
  SELECT 3 AS seq, doc_id, clause_ref, heading, 'WBP 13.1-13.3 (protection)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(13\.1 .*)$')) AS quote_snippet
  FROM c WHERE doc_id = 'P2-01' AND clause_ref = 'Part 15'
)
ORDER BY seq;
