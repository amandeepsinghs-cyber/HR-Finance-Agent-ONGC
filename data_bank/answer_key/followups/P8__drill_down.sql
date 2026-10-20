-- Answer Key Follow-up SQL: P8__drill_down
-- Question: Who is the designated Chief Vigilance Officer (CVO) / Nodal Officer for receiving Whistle Blower disclosures?
-- Type: policy
-- Semantic audit 2026-10-20: old query returned only SUBSTR(text,1,300) = the chunk's metadata header
-- (title / glossary), never the clause body, so the answer key contained no actual rule. Now strips the
-- header and extracts the specific sub-clauses that answer the question (column `provision`).
-- Semantic audit 2026-10-20: Old query returned Part 2 (statutory background). GAP: no named CVO in corpus.

WITH c AS (
  SELECT doc_id, clause_ref, heading,
         REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(text,
           r'(?s)^.*?Domain Vocabulary[^\n]*\n', ''),
           r'\\\\192\.168\.4\.1\\e\\Public Enterprises \(2018\)(\\4077PE)+\(Chapter 2\)', ' '),
           r'\d*\s*Chapter 2—Personnel Policies\s*\d*', ' '),
           r'Page \d+ of \d+', ' '),
           r'\s+', ' ') AS body
  FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
  WHERE (doc_id = 'P2-01' AND clause_ref = 'Part 4')
     OR (doc_id = 'P2-01' AND clause_ref = 'Part 5')
     OR (doc_id = 'P2-01' AND clause_ref = 'Part 7')
)
SELECT doc_id, clause_ref, heading, provision, quote_snippet
FROM (
  SELECT 1 AS seq, doc_id, clause_ref, heading, 'WBP 4.7-4.8 (Investigators incl. CVO; Nodal Officer)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(4\.7 .*?) 4\.9 ')) AS quote_snippet
  FROM c WHERE doc_id = 'P2-01' AND clause_ref = 'Part 5'
  UNION ALL
  SELECT 2 AS seq, doc_id, clause_ref, heading, 'WBP 4.4 (Competent Authority)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(4\.4 .*?) 4\.5 ')) AS quote_snippet
  FROM c WHERE doc_id = 'P2-01' AND clause_ref = 'Part 4'
  UNION ALL
  SELECT 3 AS seq, doc_id, clause_ref, heading, 'WBP 7.1 (address)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(7\.1 .*?) 7\.2 ')) AS quote_snippet
  FROM c WHERE doc_id = 'P2-01' AND clause_ref = 'Part 7'
)
ORDER BY seq;
