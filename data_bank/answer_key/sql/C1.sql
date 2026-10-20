-- Answer Key SQL: C1
-- Question: How many executives have been posted in the Delhi office for 5 years or more? Break down by grade and discipline.
-- Type: data
-- Semantic audit 2026-10-20: aligned with H10/X10 rotation rule. Due = current continuous stay >= 60 months at
-- 2026-10-19 (v_continuous_stay), minus officers retiring within 3 x 365.25 days (JRTP 7.1 practice), minus officers
-- whose current posting carries a valid exemption tag (literal 'None' = no exemption; valid_until >= 2026-10-19 or NULL).

WITH cur_exempt AS (
    SELECT emp_id, LOGICAL_OR(
        LOWER(IFNULL(exemption_tag, 'none')) NOT IN ('none', '')
        AND (exemption_valid_until IS NULL OR exemption_valid_until >= DATE '2026-10-19')) AS has_valid_exemption
    FROM posting_history
    WHERE is_current_posting
    GROUP BY emp_id
),
base AS (
    SELECT v.grade_id, v.discipline_id, v.emp_id,
           DATE_DIFF(v.retirement_date, DATE '2026-10-19', DAY) <= 3 * 365.25 AS retiring_3yr,
           IFNULL(x.has_valid_exemption, FALSE) AS has_valid_exemption
    FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay` v
    LEFT JOIN cur_exempt x ON x.emp_id = v.emp_id
    WHERE v.is_current_stay = TRUE
      AND v.wc_id = 'WC-DEL'
      AND v.grade_id LIKE 'E%'
      AND v.continuous_stay_months >= 60
)
SELECT
    grade_id,
    discipline_id,
    COUNT(DISTINCT emp_id) AS delhi_executives_ge_5yr,
    COUNT(DISTINCT IF(retiring_3yr, emp_id, NULL)) AS exempt_retiring_3yr,
    COUNT(DISTINCT IF(NOT retiring_3yr AND has_valid_exemption, emp_id, NULL)) AS exempt_valid_tag,
    COUNT(DISTINCT IF(NOT retiring_3yr AND NOT has_valid_exemption, emp_id, NULL)) AS non_exempt_due_transfer
FROM base
GROUP BY grade_id, discipline_id
ORDER BY grade_id, discipline_id;
