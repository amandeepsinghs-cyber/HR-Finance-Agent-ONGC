-- Answer Key Follow-up SQL: P10__compare_or_so_what
-- Question: How do promotion criteria compare between engineering disciplines and support services (HR, MM, Finance)?
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
     OR (doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 4.0')
     OR (doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 5.0')
)
SELECT doc_id, clause_ref, heading, provision, quote_snippet
FROM (
  SELECT 1 AS seq, doc_id, clause_ref, heading, 'R&P 5.1-5.2 (hard-station prerequisite, technical cadres)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(5\.1 .*?) \(5\.1\)')) AS quote_snippet
  FROM c WHERE doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 5.0'
  UNION ALL
  SELECT 2 AS seq, doc_id, clause_ref, heading, 'R&P 4.1-4.3 (merit channel, same for all disciplines)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(4\.1 .*?) \(4\.1\)')) AS quote_snippet
  FROM c WHERE doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 4.0'
  UNION ALL
  SELECT 3 AS seq, doc_id, clause_ref, heading, 'R&P 2.2 (time-bound, non-vacancy)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(2\.2 .*?) 2\.3 ')) AS quote_snippet
  FROM c WHERE doc_id = 'R&P/Promotion' AND clause_ref = 'Clause 2.0'
)
ORDER BY seq;
