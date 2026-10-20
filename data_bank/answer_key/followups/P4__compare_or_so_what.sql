-- Answer Key Follow-up SQL: P4__compare_or_so_what
-- Question: How does the encashment formula at retirement compare with active service leave encashment during LFA/LTC?
-- Type: policy
-- Semantic audit 2026-10-20: old query returned only SUBSTR(text,1,300) = the chunk's metadata header
-- (title / glossary), never the clause body, so the answer key contained no actual rule. Now strips the
-- header and extracts the specific sub-clauses that answer the question (column `provision`).
-- Semantic audit 2026-10-20: GAP: no LFA/LTC-linked encashment rule in corpus; 4.3 running encashment is the in-service rule.

WITH c AS (
  SELECT doc_id, clause_ref, heading,
         REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(text,
           r'(?s)^.*?Domain Vocabulary[^\n]*\n', ''),
           r'\\\\192\.168\.4\.1\\e\\Public Enterprises \(2018\)(\\4077PE)+\(Chapter 2\)', ' '),
           r'\d*\s*Chapter 2—Personnel Policies\s*\d*', ' '),
           r'Page \d+ of \d+', ' '),
           r'\s+', ' ') AS body
  FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
  WHERE (doc_id = 'Leave Rules' AND clause_ref = 'Clause 4.0')
)
SELECT doc_id, clause_ref, heading, provision, quote_snippet
FROM (
  SELECT 1 AS seq, doc_id, clause_ref, heading, 'Leave Rules 4.2 (retirement formula)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(4\.2 .*?) 4\.3 ')) AS quote_snippet
  FROM c WHERE doc_id = 'Leave Rules' AND clause_ref = 'Clause 4.0'
  UNION ALL
  SELECT 2 AS seq, doc_id, clause_ref, heading, 'Leave Rules 4.3 (in-service encashment)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(4\.3 .*?) \(4\.1\)')) AS quote_snippet
  FROM c WHERE doc_id = 'Leave Rules' AND clause_ref = 'Clause 4.0'
)
ORDER BY seq;
