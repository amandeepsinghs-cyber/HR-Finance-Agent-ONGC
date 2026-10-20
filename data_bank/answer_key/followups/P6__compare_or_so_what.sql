-- Answer Key Follow-up SQL: P6__compare_or_so_what
-- Question: How does the gift acceptance policy differ between festive occasions with personal friends and business associates?
-- Type: policy
-- Semantic audit 2026-10-20: old query returned only SUBSTR(text,1,300) = the chunk's metadata header
-- (title / glossary), never the clause body, so the answer key contained no actual rule. Now strips the
-- header and extracts the specific sub-clauses that answer the question (column `provision`).
-- Semantic audit 2026-10-20: Old query cited Rule 4 (general integrity) - did not address friend vs business giver.

WITH c AS (
  SELECT doc_id, clause_ref, heading,
         REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(text,
           r'(?s)^.*?Domain Vocabulary[^\n]*\n', ''),
           r'\\\\192\.168\.4\.1\\e\\Public Enterprises \(2018\)(\\4077PE)+\(Chapter 2\)', ' '),
           r'\d*\s*Chapter 2—Personnel Policies\s*\d*', ' '),
           r'Page \d+ of \d+', ' '),
           r'\s+', ' ') AS body
  FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
  WHERE (doc_id = 'G-06' AND clause_ref = '12. Gifts')
)
SELECT doc_id, clause_ref, heading, provision, quote_snippet
FROM (
  SELECT 1 AS seq, doc_id, clause_ref, heading, 'DPE CDA Rule 12 Explanation (who is a giver)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(Explanation - .*?) Note - ')) AS quote_snippet
  FROM c WHERE doc_id = 'G-06' AND clause_ref = '12. Gifts'
  UNION ALL
  SELECT 2 AS seq, doc_id, clause_ref, heading, 'DPE CDA Rule 12(3) (personal friends, festive)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(3\. On such occasions.*?) 4\. In any other case')) AS quote_snippet
  FROM c WHERE doc_id = 'G-06' AND clause_ref = '12. Gifts'
  UNION ALL
  SELECT 3 AS seq, doc_id, clause_ref, heading, 'DPE CDA Rule 12(4) (business associates / any other)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(4\. In any other case.*)$')) AS quote_snippet
  FROM c WHERE doc_id = 'G-06' AND clause_ref = '12. Gifts'
)
ORDER BY seq;
