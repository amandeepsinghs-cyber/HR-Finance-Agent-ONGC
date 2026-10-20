-- Answer Key Follow-up SQL: P7__drill_down
-- Question: What is the approved daily hotel reimbursement entitlement and local conveyance ceiling for Mumbai (Class-A city) for E2?
-- Type: policy
-- Semantic audit 2026-10-20: old query returned TA Regulations Part 1 (short title) - no hotel or conveyance
-- figure. Now: E2 Class-A hotel ceiling (dim_grade), lodging reimbursed on E2 Class-A claims, and the
-- local-conveyance-on-tour rate parsed from TA Regulations Part 19 (EC 483rd meeting, Apr-2016 revision).

WITH lc AS (
  SELECT SAFE_CAST(REGEXP_EXTRACT(REGEXP_REPLACE(text, r'\s+', ' '),
                   r'483rd.*?Executives up to E-6 level (\d+)') AS INT64) AS local_conveyance_per_day_inr
  FROM `ongc-hr-finance-agent.hrfin_docs.silver_chunks`
  WHERE doc_id = 'P1-16' AND clause_ref = 'Part 19'
),
cl AS (
  SELECT
      COUNT(*) AS e2_class_a_claims,
      ROUND(AVG(SAFE_DIVIDE(lodging_hotel_amount_inr, DATE_DIFF(end_date, start_date, DAY)))) AS avg_lodging_per_night_inr,
      ROUND(AVG(SAFE_DIVIDE(daily_allowance_da_inr, DATE_DIFF(end_date, start_date, DAY) + 1))) AS avg_da_per_day_inr
  FROM travel_claims
  WHERE grade_id = 'E2' AND LOWER(city_category) = 'class_a'
)
SELECT
    g.grade_id,
    'Class_A' AS city_class,
    g.daily_lodging_limit_cat_a_inr AS hotel_ceiling_per_day_inr,
    cl.avg_lodging_per_night_inr,
    cl.e2_class_a_claims,
    lc.local_conveyance_per_day_inr,
    'P1-16 TA Regulations Part 19 (EC 483rd meeting)' AS conveyance_source
FROM dim_grade g
CROSS JOIN lc
CROSS JOIN cl
WHERE g.grade_id = 'E2';
