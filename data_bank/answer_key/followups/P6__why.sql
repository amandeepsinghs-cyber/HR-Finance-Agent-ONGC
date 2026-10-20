-- Answer Key Follow-up SQL: P6__why
-- Question: Why do CVC regulations require prompt reporting and surrender of commercial vendor gifts exceeding nominal value?
-- Type: policy
-- Semantic audit 2026-10-20: old query returned only SUBSTR(text,1,300) = the chunk's metadata header
-- (title / glossary), never the clause body, so the answer key contained no actual rule. Now strips the
-- header and extracts the specific sub-clauses that answer the question (column `provision`).
-- Semantic audit 2026-10-20: GAP: no CVC gift-surrender circular in corpus; conduct-rule rationale is cited instead.

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
     OR (doc_id = 'G-06' AND clause_ref = '4. General')
     OR (doc_id = 'G-06' AND clause_ref = '5. Misconduct')
)
SELECT doc_id, clause_ref, heading, provision, quote_snippet
FROM (
  SELECT 1 AS seq, doc_id, clause_ref, heading, 'DPE CDA Rule 5(2)-(2A) (bribes, vendor sponsorship)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(2\. Taking or giving bribes.*?) 3\. Possession')) AS quote_snippet
  FROM c WHERE doc_id = 'G-06' AND clause_ref = '5. Misconduct'
  UNION ALL
  SELECT 2 AS seq, doc_id, clause_ref, heading, 'DPE CDA Rule 4(1)(xiv)-(xv) (no obligations / misuse)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(\(xiv\) .*?) \(xvi\)')) AS quote_snippet
  FROM c WHERE doc_id = 'G-06' AND clause_ref = '4. General'
  UNION ALL
  SELECT 3 AS seq, doc_id, clause_ref, heading, 'DPE CDA Rule 12 Note (lavish hospitality)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(Note - .*?) 2\. On occasions')) AS quote_snippet
  FROM c WHERE doc_id = 'G-06' AND clause_ref = '12. Gifts'
)
ORDER BY seq;
