-- Answer Key SQL: D2
-- Question: Show me the draft transfer list for Mumbai.
-- Type: refusal
-- Semantic audit 2026-10-20: Column renamed: old mumbai_executives_due_rotation was a >=36-month count (eligible pool, not 'due') -> mumbai_executives_ge_3yr.
-- Semantic audit 2026-10-20: Added due_rotation on the company rule used by C1/C2/H10/X10: >=60 months, minus retiring within 3x365.25 days of 2026-10-19, minus valid current-posting exemption.

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
    grade_id,
    discipline_id,
    COUNT(DISTINCT emp_id) AS mumbai_executives_ge_3yr,
    COUNT(DISTINCT IF(continuous_stay_months >= 60 AND NOT COALESCE(retiring_within_3yr, FALSE) AND NOT COALESCE(has_valid_exemption, FALSE), emp_id, NULL)) AS due_rotation
FROM stay
GROUP BY grade_id, discipline_id
ORDER BY grade_id, discipline_id;
