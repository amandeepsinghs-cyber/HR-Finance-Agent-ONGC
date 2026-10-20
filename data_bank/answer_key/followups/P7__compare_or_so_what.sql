-- Answer Key Follow-up SQL: P7__compare_or_so_what
-- Question: How does the lodging entitlement for Class-A cities like Mumbai and Delhi compare with Class-B field work centres?
-- Type: policy
-- Semantic audit 2026-10-20: old query listed dim_grade Cat-A limits only (no Class-B figure exists in dim_grade).
-- Now compares lodging reimbursed per night on E1-E4 travel claims by city class against the Cat-A ceiling.
-- GAP: no Class-B lodging ceiling in dim_grade or the TA Regulations text; observed claims are used.

SELECT
    t.grade_id,
    g.daily_lodging_limit_cat_a_inr AS cat_a_ceiling_inr,
    ROUND(AVG(IF(LOWER(t.city_category) = 'class_a', SAFE_DIVIDE(t.lodging_hotel_amount_inr, DATE_DIFF(t.end_date, t.start_date, DAY)), NULL))) AS class_a_per_night_inr,
    ROUND(AVG(IF(LOWER(t.city_category) = 'class_b', SAFE_DIVIDE(t.lodging_hotel_amount_inr, DATE_DIFF(t.end_date, t.start_date, DAY)), NULL))) AS class_b_per_night_inr,
    ROUND(AVG(IF(LOWER(t.city_category) = 'class_c', SAFE_DIVIDE(t.lodging_hotel_amount_inr, DATE_DIFF(t.end_date, t.start_date, DAY)), NULL))) AS class_c_per_night_inr,
    ROUND(AVG(IF(LOWER(t.city_category) = 'offshore', SAFE_DIVIDE(t.lodging_hotel_amount_inr, DATE_DIFF(t.end_date, t.start_date, DAY)), NULL))) AS offshore_per_night_inr,
    COUNT(*) AS claims
FROM travel_claims t
JOIN dim_grade g USING (grade_id)
WHERE t.grade_id IN ('E1', 'E2', 'E3', 'E4')
GROUP BY t.grade_id, g.daily_lodging_limit_cat_a_inr
ORDER BY t.grade_id;
