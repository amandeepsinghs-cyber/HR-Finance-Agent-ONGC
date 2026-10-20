-- Answer Key Follow-up SQL: D1__drill_down
-- Question: What is the published pay scale and basic pay range for my reporting officer's grade (E6)?
-- Type: refusal
-- Semantic audit 2026-10-20: Added grade/designation and band midpoint so the answer names the grade it describes; no logic change.

SELECT
    grade_id,
    designation,
    pay_scale_min_inr,
    pay_scale_max_inr,
    (pay_scale_min_inr + pay_scale_max_inr) / 2.0 AS pay_scale_midpoint_inr
FROM dim_grade
WHERE grade_id = 'E6';
