-- Answer Key Follow-up SQL: C10__drill_down
-- Question: Which specific MoU parameters (crude production, natural gas sales, capex expenditure, RRR) are currently rated below 'Excellent'?
-- Type: data
-- Semantic audit 2026-10-20: old SQL listed all 9 FY26 parameters with no rating filter (and FY26 is not
-- "currently"). Now: FY27 (current year, projected on the H1 run-rate) parameters whose recorded rating is
-- below 'Excellent' (LOWER(achieved_rating) != 'excellent'), with the shortfall to the Excellent target in
-- the parameter's own unit (LTIFR is lower-is-better) and the weight at stake.

SELECT
    parameter_name,
    unit_of_measure,
    weightage,
    excellent_target,
    actual_achievement AS fy27_projected_achievement,
    achieved_rating AS fy27_projected_rating,
    ROUND(CASE WHEN parameter_id = 'MOU-HSE-SAFETY' THEN actual_achievement - excellent_target
               ELSE excellent_target - actual_achievement END, 3) AS shortfall_to_excellent,
    weighted_score,
    ROUND(weightage / 100.0 * 5 - weighted_score, 3) AS weighted_score_forgone
FROM mou_targets
WHERE fiscal_year = 'FY27'
  AND LOWER(achieved_rating) != 'excellent'
ORDER BY weightage DESC, weighted_score_forgone DESC;
