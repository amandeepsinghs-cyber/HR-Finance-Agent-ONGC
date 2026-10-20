-- Answer Key SQL: C10
-- Question: How are we tracking against our MoU targets with MoPNG/DPE for this year?
-- Type: data
-- Semantic audit 2026-10-20: (1) FY_MAPPING - "this year" is FY27 (current FY, 2026-04..2026-09 elapsed); the
-- old SQL reported FY26. FY27 actual_achievement is the full-year projection on the H1 run-rate (e.g. crude
-- 19.051 MMT = 2 x H1 9.525 MMT in production_monthly), so it is labelled as projected. (2) PCT_DENOM - LTIFR is
-- lower-is-better, so actual/target gave 140% "achievement"; it is now inverted (target/actual) for that
-- parameter. Added the recorded rating, Very Good threshold, gap to Excellent and FY26 final rating.

SELECT
    m.parameter_name,
    m.unit_of_measure,
    m.weightage,
    m.excellent_target,
    m.very_good_target,
    m.actual_achievement AS fy27_projected_achievement,
    ROUND(CASE WHEN m.parameter_id = 'MOU-HSE-SAFETY' THEN m.excellent_target * 100.0 / NULLIF(m.actual_achievement, 0)
               ELSE m.actual_achievement * 100.0 / NULLIF(m.excellent_target, 0) END, 1) AS pct_of_excellent,
    ROUND(CASE WHEN m.parameter_id = 'MOU-HSE-SAFETY' THEN m.excellent_target - m.actual_achievement
               ELSE m.actual_achievement - m.excellent_target END, 3) AS gap_to_excellent,
    m.achieved_rating AS fy27_projected_rating,
    p.achieved_rating AS fy26_final_rating,
    m.composite_score AS fy27_composite_to_date,
    m.projected_composite_score AS fy27_projected_composite
FROM mou_targets m
LEFT JOIN mou_targets p ON p.parameter_id = m.parameter_id AND p.fiscal_year = 'FY26'
WHERE m.fiscal_year = 'FY27'
ORDER BY m.weightage DESC, pct_of_excellent ASC;
