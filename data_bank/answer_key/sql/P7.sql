-- Answer Key SQL: P7
-- Question: What is my travel class and lodging allowance for official travel to Mumbai as an E2?
-- Type: policy
-- Semantic audit 2026-10-20: dim_grade lookup was correct but the MD rendered an empty citation. Added the
-- Mumbai city class and the E2 lodging actually reimbursed on Mumbai claims (travel_claims) as corroboration.

WITH mum AS (
  SELECT
      grade_id,
      ANY_VALUE(city_category) AS mumbai_city_category,
      COUNT(*) AS e2_mumbai_claims,
      ROUND(AVG(SAFE_DIVIDE(lodging_hotel_amount_inr, DATE_DIFF(end_date, start_date, DAY)))) AS avg_lodging_per_night_inr,
      ANY_VALUE(travel_class_entitlement) AS claim_class_entitlement
  FROM travel_claims
  WHERE grade_id = 'E2' AND LOWER(to_city) = 'mumbai'
  GROUP BY grade_id
)
SELECT
    g.grade_id,
    g.designation,
    g.ta_da_travel_class,
    g.daily_lodging_limit_cat_a_inr,
    m.mumbai_city_category,
    m.e2_mumbai_claims,
    m.avg_lodging_per_night_inr,
    m.claim_class_entitlement
FROM dim_grade g
LEFT JOIN mum m USING (grade_id)
WHERE g.grade_id = 'E2';
