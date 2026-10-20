-- Provenance for DOC-CONF-002: Draft FY27 AGTO Annexure I (Delhi & Dehradun Tenure & Cumulative Cap Audit)
-- Evaluates continuous station tenure (JRTP Clause 3.0) and cumulative cluster cap (JRTP Clause 4.0)
-- Applies 3-year pre-retirement protective exemption (JRTP Clause 7.0) for E0-E9 executives (JRTP Clause 1.2)

WITH numbered_postings AS (
  SELECT
    p.PERNR as emp_id,
    p.WERKS as wc_id,
    p.PERSK as grade_id,
    p.discipline_id,
    CAST(p.BEGDA AS DATE) as from_date,
    CAST(p.ENDDA AS DATE) as to_date,
    p.is_current_posting,
    ROW_NUMBER() OVER (PARTITION BY p.PERNR ORDER BY CAST(p.BEGDA AS DATE), p.posting_id) -
    ROW_NUMBER() OVER (PARTITION BY p.PERNR, p.WERKS ORDER BY CAST(p.BEGDA AS DATE), p.posting_id) AS island_id
  FROM 'landing/sap/PA0001.csv' p
),
islands AS (
  SELECT
    emp_id,
    wc_id,
    island_id,
    MIN(from_date) AS continuous_from_date,
    MAX(COALESCE(to_date, DATE '2026-10-19')) AS continuous_to_date,
    BOOL_OR(to_date IS NULL OR is_current_posting) AS is_current_stay,
    MAX(grade_id) AS current_grade_id,
    MAX(discipline_id) AS current_discipline_id,
    DATEDIFF('month', MIN(from_date), DATE '2026-10-19') AS continuous_stay_months,
    ROUND(DATEDIFF('day', MIN(from_date), DATE '2026-10-19') / 365.25, 2) AS continuous_stay_years
  FROM numbered_postings
  GROUP BY emp_id, wc_id, island_id
),
v_stay AS (
  SELECT
    i.emp_id,
    e.name AS emp_name,
    CAST(e.retirement_date AS DATE) as retirement_date,
    i.wc_id,
    i.current_grade_id AS grade_id,
    i.current_discipline_id AS discipline_id,
    i.continuous_from_date,
    i.continuous_to_date,
    i.continuous_stay_months,
    i.continuous_stay_years,
    i.is_current_stay
  FROM islands i
  JOIN 'landing/sap/PA0002_PA0001.csv' e ON i.emp_id = e.PERNR
  WHERE e.STAT2 = 'Active' AND i.current_grade_id LIKE 'E%'
),
stay_summary AS (
  SELECT
    wc_id as scope,
    'station_tenure_ge_5yr' as audit_type,
    COUNT(DISTINCT emp_id) AS total_count,
    COUNT(DISTINCT CASE WHEN DATEDIFF('day', DATE '2026-10-19', retirement_date) <= 3 * 365.25 THEN emp_id END) AS exempt_count,
    COUNT(DISTINCT CASE WHEN DATEDIFF('day', DATE '2026-10-19', retirement_date) > 3 * 365.25 THEN emp_id END) AS due_transfer_count
  FROM v_stay
  WHERE is_current_stay = TRUE
    AND wc_id IN ('WC-DEL', 'WC-DDN')
    AND continuous_stay_months >= 60
  GROUP BY wc_id
),
posting_clusters AS (
  SELECT
    p.PERNR AS emp_id,
    DATEDIFF('day', CAST(p.BEGDA AS DATE), COALESCE(CAST(p.ENDDA AS DATE), DATE '2026-10-19')) AS stint_days,
    p.is_current_posting
  FROM 'landing/sap/PA0001.csv' p
  WHERE p.WERKS = 'WC-DEL'
),
cluster_agg AS (
  SELECT
    pc.emp_id,
    ROUND(SUM(pc.stint_days) / 365.25, 2) AS cumulative_cluster_years,
    BOOL_OR(pc.is_current_posting) AS is_currently_in_cluster
  FROM posting_clusters pc
  GROUP BY pc.emp_id
),
cap_summary AS (
  SELECT
    'CL-DEL' as scope,
    'cluster_cumulative_cap_ge_10yr' as audit_type,
    COUNT(DISTINCT CASE WHEN c.cumulative_cluster_years >= 10.0 THEN c.emp_id END) AS total_count,
    COUNT(DISTINCT CASE WHEN c.cumulative_cluster_years >= 10.0 AND DATEDIFF('day', DATE '2026-10-19', CAST(e.retirement_date AS DATE)) <= 3 * 365.25 THEN c.emp_id END) AS exempt_count,
    COUNT(DISTINCT CASE WHEN c.cumulative_cluster_years >= 10.0 AND DATEDIFF('day', DATE '2026-10-19', CAST(e.retirement_date AS DATE)) > 3 * 365.25 THEN c.emp_id END) AS due_transfer_count
  FROM cluster_agg c
  JOIN 'landing/sap/PA0002_PA0001.csv' e ON c.emp_id = e.PERNR
  WHERE c.is_currently_in_cluster = TRUE
)
SELECT * FROM stay_summary
UNION ALL
SELECT * FROM cap_summary
ORDER BY audit_type, scope;