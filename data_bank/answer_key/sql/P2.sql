-- Answer Key SQL: P2
-- Question: Which stations count as one cluster for tenure purposes?
-- Type: policy
-- Semantic audit 2026-10-20: old query returned the JRTP 5.0 metadata header (no cluster list) plus 4 TA-regulation
-- chunks (P1-16) irrelevant to clusters. Now lists the 13 clusters from dim_work_centre (structured) with
-- their work centres and checks each is named in JRTP Clause 5.2.

WITH doc AS (
  SELECT REGEXP_REPLACE(text, r'\s+', ' ') AS body
  FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
  WHERE doc_id = 'JRTP' AND clause_ref = 'Clause 5.0'
)
SELECT
    w.cluster_id,
    w.cluster_name,
    COUNT(*) AS work_centres,
    STRING_AGG(DISTINCT w.city, ', ' ORDER BY w.city) AS cities,
    STRING_AGG(w.short_name, '; ' ORDER BY w.wc_id) AS work_centre_names,
    LOGICAL_AND(STRPOS(doc.body, CONCAT('Cluster ', w.cluster_id, ' ')) > 0) AS listed_in_jrtp_5_2
FROM dim_work_centre w
CROSS JOIN doc
GROUP BY w.cluster_id, w.cluster_name
ORDER BY work_centres DESC, w.cluster_id;
