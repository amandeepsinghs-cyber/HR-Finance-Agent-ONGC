-- Answer Key Follow-up SQL: P8__why
-- Question: Why does the Whistle Blower policy provide explicit safeguards against reprisal and retaliatory service transfers?
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
  WHERE (doc_id = 'P2-01' AND clause_ref = 'Part 15')
     OR (doc_id = 'P2-01' AND clause_ref = 'Part 16')
     OR (doc_id = 'P2-01' AND clause_ref = 'Part 3')
)
SELECT doc_id, clause_ref, heading, provision, quote_snippet
FROM (
  SELECT 1 AS seq, doc_id, clause_ref, heading, 'WBP 3.2-3.3 (objectives)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(3\.2 .*)$')) AS quote_snippet
  FROM c WHERE doc_id = 'P2-01' AND clause_ref = 'Part 3'
  UNION ALL
  SELECT 2 AS seq, doc_id, clause_ref, heading, 'WBP 13.1 (anti-retaliation incl. transfer)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(13\.1 .*?) 13\.2 ')) AS quote_snippet
  FROM c WHERE doc_id = 'P2-01' AND clause_ref = 'Part 15'
  UNION ALL
  SELECT 3 AS seq, doc_id, clause_ref, heading, 'WBP 14.1-14.3 (limits of protection)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(14\.1 .*?) 15\. COMMUNICATION')) AS quote_snippet
  FROM c WHERE doc_id = 'P2-01' AND clause_ref = 'Part 16'
)
ORDER BY seq;
