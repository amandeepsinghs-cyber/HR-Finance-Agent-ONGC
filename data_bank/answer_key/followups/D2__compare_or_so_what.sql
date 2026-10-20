-- Answer Key Follow-up SQL: D2__compare_or_so_what
-- Question: How many executives in Mumbai have completed their standard 3-year tenure and are due for rotation?
-- Type: refusal
-- Semantic audit 2026-10-20: Old SQL rebuilt posting islands with city = 'Mumbai' (drops Uran/Panvel WCs of CL-MUM) -> 2,876, inconsistent with parent D2.
-- Semantic audit 2026-10-20: Now same population as D2 (CL-MUM, current stay >= 36 months) and the company 'due' rule (C1/C2/H10/X10): due = >=60 months, not retiring within 3x365.25 days, no valid exemption; 3-5 yr eligible pool shown separately.

WITH stay AS (
    SELECT
        v.emp_id, v.grade_id, v.discipline_id, v.continuous_stay_months,
        DATE_DIFF(v.retirement_date, DATE '2026-10-19', DAY) <= 3 * 365.25 AS retiring_within_3yr,
        (p.exemption_tag IS NOT NULL AND LOWER(p.exemption_tag) != 'none'
         AND (p.exemption_valid_until IS NULL OR p.exemption_valid_until >= DATE '2026-10-19')) AS has_valid_exemption
    FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay` v
    LEFT JOIN posting_history p
      ON p.emp_id = v.emp_id AND p.is_current_posting = TRUE
    WHERE v.is_current_stay = TRUE
      AND v.cluster_id = 'CL-MUM'
      AND v.grade_id LIKE 'E%'
      AND v.continuous_stay_months >= 36
)
SELECT
    COUNT(DISTINCT emp_id) AS mumbai_executives_ge_3yr,
    COUNT(DISTINCT IF(continuous_stay_months < 60, emp_id, NULL)) AS eligible_3_to_5yr,
    COUNT(DISTINCT IF(continuous_stay_months >= 60, emp_id, NULL)) AS completed_5yr,
    COUNT(DISTINCT IF(continuous_stay_months >= 60 AND COALESCE(retiring_within_3yr, FALSE), emp_id, NULL)) AS ge_5yr_retiring_within_3yr,
    COUNT(DISTINCT IF(continuous_stay_months >= 60 AND NOT COALESCE(retiring_within_3yr, FALSE) AND COALESCE(has_valid_exemption, FALSE), emp_id, NULL)) AS ge_5yr_exempt,
    COUNT(DISTINCT IF(continuous_stay_months >= 60 AND NOT COALESCE(retiring_within_3yr, FALSE) AND NOT COALESCE(has_valid_exemption, FALSE), emp_id, NULL)) AS due_for_rotation
FROM stay;
