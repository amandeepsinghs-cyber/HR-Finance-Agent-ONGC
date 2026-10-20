-- Answer Key Follow-up SQL: P9__compare_or_so_what
-- Question: What interim relief and workplace protection measures can the ICC recommend during an ongoing inquiry?
-- Type: policy
-- Semantic audit 2026-10-20: old query returned only SUBSTR(text,1,300) = the chunk's metadata header
-- (title / glossary), never the clause body, so the answer key contained no actual rule. Now strips the
-- header and extracts the specific sub-clauses that answer the question (column `provision`).
-- Semantic audit 2026-10-20: Old query returned 5 arbitrary CDA (P1-01) disciplinary fragments. GAP: no POSH Act / ICC procedure
-- document (interim relief under s.12) is in the corpus; closest provisions cited.

WITH c AS (
  SELECT doc_id, clause_ref, heading,
         REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(text,
           r'(?s)^.*?Domain Vocabulary[^\n]*\n', ''),
           r'\\\\192\.168\.4\.1\\e\\Public Enterprises \(2018\)(\\4077PE)+\(Chapter 2\)', ' '),
           r'\d*\s*Chapter 2—Personnel Policies\s*\d*', ' '),
           r'Page \d+ of \d+', ' '),
           r'\s+', ' ') AS body
  FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
  WHERE (doc_id = 'G-06' AND clause_ref = '25. Procedure for imposing major penalties')
     OR (doc_id = 'P2-16' AND clause_ref = 'Part 4')
     OR (doc_id = 'P2-16' AND clause_ref = 'Part 8')
)
SELECT doc_id, clause_ref, heading, provision, quote_snippet
FROM (
  SELECT 1 AS seq, doc_id, clause_ref, heading, 'DPE CDA Rule 25 proviso (Complaints Committee = inquiring authority)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(Provided that where there is a complaint of sexual harassment.*?)$')) AS quote_snippet
  FROM c WHERE doc_id = 'G-06' AND clause_ref = '25. Procedure for imposing major penalties'
  UNION ALL
  SELECT 2 AS seq, doc_id, clause_ref, heading, 'Human Rights Policy 3.2 (prevention of harassment)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(3\.2 Prevention of Harassment.*?) 3\.3 ')) AS quote_snippet
  FROM c WHERE doc_id = 'P2-16' AND clause_ref = 'Part 4'
  UNION ALL
  SELECT 3 AS seq, doc_id, clause_ref, heading, 'Human Rights Policy 4 (ICC as redressal channel)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(4\. Grievance Redressal.*)$')) AS quote_snippet
  FROM c WHERE doc_id = 'P2-16' AND clause_ref = 'Part 8'
)
ORDER BY seq;
