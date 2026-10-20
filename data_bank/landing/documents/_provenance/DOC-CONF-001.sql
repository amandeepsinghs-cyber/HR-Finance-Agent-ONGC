-- Provenance for Draft FY27 AGTO Master Proposal
-- Note: Reads cleaned workbook from landing/excel/_clean/manpower_plan.xlsx (reconstructed from messy landing source)
-- JRTP Clause 1.2 (E0-E9 executives only), Clause 3.0 (Station Tenure), Clause 7.0 (Pre-Retirement Exemption)
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
    DATEDIFF('month', MIN(from_date), DATE '2026-10-19') AS continuous_stay_months
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
    i.continuous_stay_months,
    i.is_current_stay
  FROM islands i
  JOIN 'landing/sap/PA0002_PA0001.csv' e ON i.emp_id = e.PERNR
  WHERE e.STAT2 = 'Active' AND i.current_grade_id LIKE 'E%'
)
SELECT emp_id, emp_name, grade_id, discipline_id, wc_id as current_wc_id, continuous_stay_months,
       'WC-ASM' as proposed_dest_wc_id, 'Assam Asset' as proposed_dest_name
FROM v_stay
WHERE is_current_stay = TRUE AND wc_id IN ('WC-DEL', 'WC-DDN', 'WC-AHM', 'WC-MEH')
  AND continuous_stay_months >= 36
  AND DATEDIFF('day', DATE '2026-10-19', retirement_date) > 3 * 365.25
ORDER BY continuous_stay_months DESC, emp_id
LIMIT 20;