-- Answer Key Follow-up SQL: T2__drill_down
-- Question: Which of the 412 Delhi-based executives with 5+ years hold technical designations needed in Assam or Tripura?
-- Type: chain
-- Semantic audit 2026-10-20: Old SQL grouped all Delhi executives by grade/discipline without any technical filter or link to Assam/Tripura needs.
-- Semantic audit 2026-10-20: Now: technical-discipline Delhi 5yr+ executives by discipline, movable (non-exempt) count, and FY26 executive vacancies in the same discipline at Assam and Tripura.

WITH delhi5 AS (
    SELECT v.emp_id, v.discipline_id, v.retirement_date
    FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay` v
WHERE v.is_current_stay AND v.wc_id = 'WC-DEL' AND v.grade_id LIKE 'E%' AND v.continuous_stay_months >= 60
),
ne_vac AS (
    SELECT
        discipline_id,
        SUM(IF(wc_id = 'WC-ASM', vacancy_count, 0)) AS assam_vac,
        SUM(IF(wc_id = 'WC-TRI', vacancy_count, 0)) AS tripura_vac
    FROM sanctioned_posts
    WHERE fiscal_year = 'FY26' AND wc_id IN ('WC-ASM', 'WC-TRI') AND LOWER(grade_band) != 'non_executive'
    GROUP BY discipline_id
)
SELECT
    d.discipline_id,
    d.name AS discipline_name,
    COUNT(DISTINCT x.emp_id) AS delhi_5yr_execs,
    COUNT(DISTINCT IF(DATE_DIFF(x.retirement_date, DATE '2026-10-19', DAY) > 3 * 365.25, x.emp_id, NULL)) AS movable_non_exempt,
    COALESCE(MAX(n.assam_vac), 0) AS assam_exec_vacancies,
    COALESCE(MAX(n.tripura_vac), 0) AS tripura_exec_vacancies,
    COALESCE(MAX(n.assam_vac), 0) + COALESCE(MAX(n.tripura_vac), 0) > 0 AS needed_in_assam_or_tripura
FROM delhi5 x
JOIN dim_discipline d ON d.discipline_id = x.discipline_id
LEFT JOIN ne_vac n ON n.discipline_id = x.discipline_id
WHERE LOWER(d.function) = 'technical'
GROUP BY d.discipline_id, d.name
ORDER BY needed_in_assam_or_tripura DESC, delhi_5yr_execs DESC;
