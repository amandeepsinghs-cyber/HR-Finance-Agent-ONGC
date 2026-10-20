-- Answer Key Follow-up SQL: H8__compare_or_so_what
-- Question: How does our training investment per employee compare with the target set in the MoU with DPE?
-- Type: data
-- Semantic audit 2026-10-20: old SQL averaged hours per record against MAX(actual) from a cross-joined MoU table. Now: per full FY
-- (FY25, FY26) the DPE MoU person-day targets and reported achievement vs person-days in training_records, and person-days per
-- employee on the FY-end headcount (stock, month YYYY-03). Rupee training investment is not in the data (GAP).
WITH mou AS (
    SELECT fiscal_year, good_target, very_good_target, excellent_target, actual_achievement, achieved_rating
    FROM mou_targets
    WHERE parameter_id = 'MOU-HR-TRAINING' AND fiscal_year IN ('FY25', 'FY26')
),
rec AS (
    SELECT fiscal_year, SUM(training_days) AS records_person_days
    FROM training_records WHERE fiscal_year IN ('FY25', 'FY26')
    GROUP BY 1
),
hc AS (
    SELECT CASE month WHEN '2025-03' THEN 'FY25' WHEN '2026-03' THEN 'FY26' END AS fiscal_year, SUM(headcount) AS fy_end_headcount
    FROM headcount_snapshot WHERE month IN ('2025-03', '2026-03')
    GROUP BY 1
)
SELECT
    m.fiscal_year,
    m.good_target, m.very_good_target, m.excellent_target,
    m.actual_achievement AS mou_reported_person_days,
    m.achieved_rating,
    r.records_person_days,
    h.fy_end_headcount,
    ROUND(m.actual_achievement / h.fy_end_headcount, 2) AS mou_person_days_per_employee,
    ROUND(r.records_person_days / h.fy_end_headcount, 2) AS records_person_days_per_employee,
    ROUND(m.very_good_target / h.fy_end_headcount, 2) AS very_good_target_per_employee
FROM mou m
JOIN rec r USING (fiscal_year)
JOIN hc h USING (fiscal_year)
ORDER BY m.fiscal_year;
