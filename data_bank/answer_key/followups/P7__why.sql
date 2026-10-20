-- Answer Key Follow-up SQL: P7__why
-- Question: Why does the TA/DA policy mandate booking air tickets through designated travel partners (Balmer Lawrie/IRCTC)?
-- Type: policy
-- Semantic audit 2026-10-20: old query returned only SUBSTR(text,1,300) = the chunk's metadata header
-- (title / glossary), never the clause body, so the answer key contained no actual rule. Now strips the
-- header and extracts the specific sub-clauses that answer the question (column `provision`).
-- Semantic audit 2026-10-20: GAP: Balmer Lawrie / IRCTC designated agents are not named anywhere in the corpus; the closest rule is
-- the check-fare / most-economical-fare booking mandate (P1-16 4.2.1 h). Old query cited Part 2 (definitions).

WITH c AS (
  SELECT doc_id, clause_ref, heading,
         REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(text,
           r'(?s)^.*?Domain Vocabulary[^\n]*\n', ''),
           r'\\\\192\.168\.4\.1\\e\\Public Enterprises \(2018\)(\\4077PE)+\(Chapter 2\)', ' '),
           r'\d*\s*Chapter 2—Personnel Policies\s*\d*', ' '),
           r'Page \d+ of \d+', ' '),
           r'\s+', ' ') AS body
  FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
  WHERE (doc_id = 'P1-16' AND clause_ref = 'Part 10')
     OR (doc_id = 'P1-16' AND clause_ref = 'Part 9')
)
SELECT doc_id, clause_ref, heading, provision, quote_snippet
FROM (
  SELECT 1 AS seq, doc_id, clause_ref, heading, 'TA Regs 4.2.1(g)-(h) (air class, check fare)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(g\. Executive Directors.*)$')) AS quote_snippet
  FROM c WHERE doc_id = 'P1-16' AND clause_ref = 'Part 9'
  UNION ALL
  SELECT 2 AS seq, doc_id, clause_ref, heading, 'TA Regs 4.2.1(h)(i)-(v) (booking rules)' AS provision, TRIM(REGEXP_EXTRACT(body, r'(i\) .*?) 4\.2\.1\.A')) AS quote_snippet
  FROM c WHERE doc_id = 'P1-16' AND clause_ref = 'Part 10'
)
ORDER BY seq;
