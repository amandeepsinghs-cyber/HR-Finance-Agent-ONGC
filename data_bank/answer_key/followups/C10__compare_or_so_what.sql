-- Answer Key Follow-up SQL: C10__compare_or_so_what
-- Question: What is the projected year-end composite score under current trends compared to the 'Excellent' rating achieved in FY25?
-- Type: data
-- Semantic audit 2026-10-20: old SQL only counted parameters and summed weightage per year (always 9 / 100),
-- with no composite score. Now per FY (FY25, FY26, FY27): recorded composite score, projected year-end
-- composite (FY27 = current trend), number of parameters rated Excellent / Very Good / Good and the weight
-- rated Excellent. (composite_score / projected_composite_score are repeated on every parameter row of a
-- year, so they are taken with ANY_VALUE, not summed.)

SELECT
    fiscal_year,
    ANY_VALUE(composite_score) AS composite_score,
    ANY_VALUE(projected_composite_score) AS projected_year_end_composite,
    ROUND(SUM(weighted_score), 2) AS sum_weighted_scores,
    COUNTIF(LOWER(achieved_rating) = 'excellent') AS params_excellent,
    COUNTIF(LOWER(achieved_rating) = 'very good') AS params_very_good,
    COUNTIF(LOWER(achieved_rating) = 'good') AS params_good,
    SUM(IF(LOWER(achieved_rating) = 'excellent', weightage, 0)) AS weight_rated_excellent,
    COUNT(*) AS parameters
FROM mou_targets
WHERE fiscal_year IN ('FY25', 'FY26', 'FY27')
GROUP BY fiscal_year
ORDER BY fiscal_year;
