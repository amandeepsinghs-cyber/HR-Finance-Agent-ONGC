-- Answer Key Follow-up SQL: X3__compare_or_so_what
-- Question: How does the safety incident frequency rate (LTIFR) in high-overtime assets compare with the corporate safety target?
-- Type: data
-- Semantic audit 2026-10-20: FY26 pooled LTIFR for high-overtime offshore assets vs company and the FY26 MoU LTIFR target bands.
-- Old SQL averaged monthly per-row LTIFRs across all work centres and years with an MoU row (FY25-FY27) - neither the
-- high-overtime population nor a single year.
WITH rates AS (
    SELECT
        ROUND(COUNTIF(lost_time_injury_flag AND monthly_overtime_hours_per_worker >= 50) * 1e6
              / SUM(IF(monthly_overtime_hours_per_worker >= 50, total_manhours_worked, 0)), 3) AS high_overtime_ltifr_fy26,
        ROUND(COUNTIF(lost_time_injury_flag AND monthly_overtime_hours_per_worker < 50) * 1e6
              / SUM(IF(monthly_overtime_hours_per_worker < 50, total_manhours_worked, 0)), 3) AS standard_overtime_ltifr_fy26,
        ROUND(COUNTIF(lost_time_injury_flag) * 1e6 / SUM(total_manhours_worked), 3) AS company_ltifr_fy26_computed
    FROM hse_incidents
    WHERE fiscal_year = 'FY26'
)
SELECT
    r.high_overtime_ltifr_fy26,
    r.standard_overtime_ltifr_fy26,
    r.company_ltifr_fy26_computed,
    m.actual_achievement AS mou_reported_ltifr_fy26,
    m.excellent_target AS mou_excellent_target,
    m.very_good_target AS mou_very_good_target,
    m.good_target AS mou_good_target,
    m.fair_target AS mou_fair_target,
    m.poor_target AS mou_poor_target,
    ROUND(r.high_overtime_ltifr_fy26 / m.excellent_target, 1) AS high_overtime_vs_excellent_multiple
FROM rates r
CROSS JOIN mou_targets m
WHERE m.fiscal_year = 'FY26' AND m.parameter_id = 'MOU-HSE-SAFETY';
